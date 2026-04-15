#!/usr/bin/env python3
"""
MCP工具参数补充主工作流

输入：巡检分析报告JSON文件，包含：
  - alertInfo: 报告元数据（report_time, cluster_name）
  - action_names: 需要处理的工具名称列表
  - actionBasics: 带基础信息的动作列表
  - abnormalInstances: 异常实例列表

输出：带data字段的actions数组（JSON格式）

工作流程：
1. 从报告中加载actionBasics、abnormalInstances、alertInfo和action_names
2. 提取所有需要参数定义的工具名称（tool_name_en）
3. 调用API批量获取工具参数定义
4. 为每个动作使用LLM+规则引擎填充data参数
5. 合并并输出最终的actions数组

命令行参数：
  --input-file, -i   输入JSON文件路径（必需）
  --output-file, -o  输出JSON文件路径（可选，默认输出到stdout）
  --verbose, -v      启用详细日志（可选）

环境变量：
- MCP_API_BASE_URL: MCP API基础URL（必需）
- MCP_API_USERNAME: MCP API用户名（必需）
- MCP_API_PASSWORD: MCP API密码（必需）
- MCP_API_APP_ID: MCP API应用ID（必需）
- MCP_API_TIMEOUT: API请求超时秒数（默认10）
- LLM_API_KEY: 阿里云百炼API Key（可选，为空则跳过LLM）
- LLM_BASE_URL: LLM API地址（默认https://dashscope.aliyuncs.com/compatible-mode/v1）
- LLM_MODEL: LLM模型版本（默认qwen3.5-plus）
- LLM_MAX_TOKENS: LLM最大输出token数（默认512）
- LLM_TIMEOUT: LLM请求超时秒数（默认30）
"""

import sys
import json
import asyncio
import argparse
from scripts.config import MCP_API_CONFIG, LLM_CONFIG
from scripts.load_data_node import LoadDataNode
from scripts.fetch_tool_args_node import FetchToolArgsNode
from scripts.fill_params_node import FillParamsNode


async def async_main(args):
    """异步主函数"""
    # 为stdout/stderr设置UTF-8编码，避免Windows上出现UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    # 1. 读取输入文件
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[错误] 无效的JSON输入: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"[错误] 输入文件未找到: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. 从报告中加载所有数据
    if args.verbose:
        print("[步骤1] 从报告中加载数据...")

    action_basics = LoadDataNode.load_action_basics(report)
    if not action_basics:
        print("[错误] 未找到actionBasics", file=sys.stderr)
        sys.exit(1)

    abnormal_instances = LoadDataNode.load_abnormal_instances(report)
    alert_info = LoadDataNode.load_alert_info(report)
    action_names = LoadDataNode.load_action_names(report)

    if args.verbose:
        print(f"  ✓ 已加载 {len(action_basics)} 个动作")
        print(f"  ✓ 已加载 {len(abnormal_instances)} 个异常实例")
        print(f"  ✓ 已加载告警信息: {alert_info}")
        print(f"  ✓ 已加载 {len(action_names)} 个动作名称")

    # 3. 从action_basics中提取所有工具名称（如果action_names为空）
    if not action_names:
        tool_names = [
            ab["tool_name_en"]
            for ab in action_basics
            if ab.get("action_tag") != "human"
        ]
    else:
        # 使用输入中的action_names，但过滤掉手动操作
        # 将action_names与tool_name_cn匹配，而不是tool_name_en
        tool_names = []
        for ab in action_basics:
            if (
                ab.get("action_tag") != "human"
                and ab.get("tool_name_cn") in action_names
            ):
                tool_names.append(ab["tool_name_en"])
        print(f"可以执行的行动列表为：{tool_names}")

    if not tool_names:
        if args.verbose:
            print("[警告] 所有动作都是手动操作或没有有效的工具名称，无需参数填充")
        # 直接输出action_basics（data字段为空）
        output_actions = []
        for ab in action_basics:
            output_action = {k: v for k, v in ab.items() if not k.startswith("_")}
            output_action["data"] = {}
            output_actions.append(output_action)

        result = {"actions": output_actions}
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 5. 批量获取工具参数定义（使用异步客户端）
    if args.verbose:
        print("[步骤2] 获取工具参数定义...")

    tool_args_map, unique_tools = await FetchToolArgsNode.batch_fetch_tool_args(
        tool_names, MCP_API_CONFIG
    )

    # 7. 填充参数并输出
    if args.verbose:
        print("[步骤3] 填充参数并输出...")

    # 直接使用输入报告中的alert_info
    actions ,action_basics_add_info= FillParamsNode.build_actions(
        action_basics, tool_args_map, action_names, alert_info, abnormal_instances
    )

    # 8. 输出最终结果
    if args.verbose:
        print("[步骤4] 打印或输出最终结果")
    report.update({"actions":actions["actions"] if "actions" in actions else actions,
                   "alertInfo":alert_info,
                   "action_basics":action_basics_add_info
                   })
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    """同步主函数，包装异步逻辑"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="MCP工具参数补充",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input-file", help="输入JSON文件路径（必需）", default="test_input_v1.json"
    )
    parser.add_argument(
        "-o", "--output-file", help="输出JSON文件路径（默认输出到stdout）",default="test_output_v1.json"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="启用详细日志",default=True)

    args = parser.parse_args()

    # 运行异步主函数
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

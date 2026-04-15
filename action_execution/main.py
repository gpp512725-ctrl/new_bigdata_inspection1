import json
import logging
import sys
import argparse
from datetime import datetime

from scripts.config import config
from scripts.mcp_client import mcp_client
from scripts.result_judge import result_judge
from scripts.llm_client import llm_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ActionExecutor:
    """行动执行器类，用于执行行动并汇总结果"""

    def execute_actions(self, actions: list[dict], alert_info: dict) -> dict:
        """循环执行所有行动并汇总结果。

        Args:
            actions: 行动信息列表，每个元素为一个 action 对象。

        Returns:
            包含 action_res 的结构化结果字典。
        """
        action_res = []

        for action in actions:
            tool_name_cn = action["tool_name_cn"]
            tool_name_en = action["tool_name_en"]
            action_des = action["action_des"]
            feature_code = action.get("feature_code", "")
            data = action.get("data", "")
            instance_id = action.get("instance_id", "")

            logger.info("开始执行行动: %s - %s", tool_name_cn, action_des)

            # 步骤 2: 调用 MCP 工具
            mcp_result = mcp_client.call_mcp_tool(action)

            # 步骤 3: 判断执行是否成功
            success = result_judge.is_success(mcp_result)

            # 步骤 4: 生成文案
            if success:
                code = 1
                action_msg = f"{tool_name_cn}为MCP执行，且执行成功"
            else:
                code = 0
                error_info = mcp_result["execute_content"]
                action_msg = llm_client.generate_failure_message(
                    action, error_info, alert_info
                )

            now = datetime.now()
            execute_time = now.strftime("%Y-%m-%d %H:%M:%S")
            # 步骤 5: 汇总单条结果
            action_res.append(
                {
                    "tool_name_cn": tool_name_cn,
                    "instance_id": instance_id,
                    "feature_code": feature_code,
                    "execute_time": execute_time,
                    "action_des": action_des,
                    "code": code,
                    "action_msg": action_msg,
                }
            )

            logger.info("行动执行完成: %s, code=%d", tool_name_cn, code)

        return action_res

    def run(self, input_file=None,output_file=None):
        """运行行动执行器，从文件或标准输入读取输入，执行行动并将结果写入文件。

        Args:
            input_file: 输入文件路径，如果为 None 则从标准输入读取。
        """
        # 读取输入数据
        if input_file:
            with open(input_file, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        else:
            input_data = json.load(sys.stdin)

        # 保存输入数据到 input.json
        with open(config.FILES["input"], "w", encoding="utf-8") as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)

        actions = input_data.get("actions", [])
        alert_info = input_data.get("alertInfo", {})
        if not actions:
            logger.warning("输入的 actions 列表为空")
            result = {"action_res": []}
        else:
            # 步骤 1: 日志输出解析信息
            logger.info("共接收到 %d 个行动", len(actions))

            # 步骤 2-5: 循环执行并汇总
            result = self.execute_actions(actions, alert_info)

        # 保存结果到 output.json
        input_data.update({"action_res": result})
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)

        # 步骤 6: 输出 JSON 格式的 action_res
        logger.info(json.dumps(input_data, ensure_ascii=False, indent=2))


def main():
    """主入口"""
    """同步主函数，包装异步逻辑"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="MCP行动执行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input-file", help="输入JSON文件路径（必需）", default="test_input_v1.json"
    )
    parser.add_argument(
        "-o", "--output-file", help="输出JSON文件路径（默认输出到stdout）",default="test_output_v1.json"
    )

    args = parser.parse_args()
    executor = ActionExecutor()
    executor.run(args.input_file,args.output_file)


if __name__ == "__main__":
    main()

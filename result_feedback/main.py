import json
import logging
import sys
import asyncio
import argparse

from scripts.abnormal_judgment import AbnormalJudgment
from scripts.feature_builder import FeatureBuilder
from scripts.feedback_builder import FeedbackBuilder
from scripts.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run(action_res: list[dict],
        action_basics: list[dict],
        alert_info: dict | None = None) -> dict:
    """结果反馈主流程入口函数。

    Args:
        action_res: 行动执行 Skill 输出的执行结果列表
        action_basics: 巡检分析报告 Skill 输出的建议行动信息列表
        alert_info: 告警信息（非空=故障分析, 空=智能巡检）。

    Returns:
        包含 execute_conclusion 的结构化字典
    """

    # ── 步骤 1: 得到异常判断入参（巡检和故障），得到每个行动的执行情况──
    logger.info("步骤 1: 得到异常判断入参（巡检和故障），得到每个行动的执行情况")
    feature_infos = await FeatureBuilder.build_all_info(action_basics,action_res,alert_info)

    # ── 步骤 2: 验证 featureInfos 异常状态 ──
    logger.info("步骤 2: 调用异常判断 API 验证特征")
    abnormal_judgment = AbnormalJudgment()
    judgment_results = await abnormal_judgment.call_abnormal_judgment_api(feature_infos["featureInfos"], [],False)
    if feature_infos["alert_bool"] :
        alert_judgment_results = await abnormal_judgment.call_abnormal_judgment_api(feature_infos["alert_feature"], [],False)
    else:
        alert_judgment_results=None

    # ── 步骤 3: 构造 feature_to_actions ──
    logger.info("步骤 3: 按特征分组行动结果")
    check_info = FeedbackBuilder.build_feature_to_actions(feature_infos["action_res_all"],feature_infos["featureInfos"],judgment_results)



    # ── 步骤 4: LLM 生成修复结论 ──
    logger.info("步骤 4: LLM 生成修复结论")
    llm_conclusion = LLMClient.generate_conclusion(check_info)


    # # ── 步骤 5: 组合最终结论 execute_conclusion ──
    logger.info("步骤 5: 组合最终结论 execute_conclusion")
    execute_conclusion = _build_execute_conclusion(
        feature_infos["alert_bool"],  feature_infos["unique_feature"], 
        llm_conclusion, alert_judgment_results, feature_infos["alert_feature"]
    )


    return execute_conclusion


def _build_execute_conclusion(alert_bool: bool,
                              unique_feature,
                              llm_conclusion: str,
                              alert_abnormal_res: list[dict],
                              alert_feature: list[dict]) -> list[dict]:
    """步骤 10：生成最终结论 execute_conclusion（array<object>）。

    - 故障分析场景 (alert_bool=True):  conclusion=alert_msg, + instance_id + feature_code=alert_feature.feature_code
    - 智能巡检场景 (alert_bool=False): conclusion=conclusion, + instance_id + feature_code

    以 (feature_code, instance_id) 为唯一键生成每条记录。
    """
    if alert_bool:
        # 检查异常结果
        alert_feature = alert_feature[0]
        execute_suc = False
        for info in alert_abnormal_res:
            instance_id = info['instance_id']
            feature_code = info['feature_code']
            # 检查特征
            if instance_id == alert_feature['instance_id'] and feature_code == alert_feature['feature_code']:
                if info['result']:
                    execute_suc = True

        unique_feature_str = ",".join(unique_feature)
        alert_msg = ""
        if execute_suc:
            alert_msg = f"检测到示例id{alert_feature['instance_id']}的{alert_feature['feature_code']}特征已恢复正常，故障已修复。故障链特征包括{unique_feature_str}。\n修复过长说明：\n"
        else:
            alert_msg = f"检测到示例id{alert_feature['instance_id']}的{alert_feature['feature_code']}特征尚未恢复正常，故障链特征包括{unique_feature_str}。\n修复过长说明：\n"
        conclusion = "\n\n".join([i["conclusion"] for i in llm_conclusion ])
        execute_conclusion = [{"feature_code": alert_feature['feature_code'],
                               "instance_id": alert_feature['instance_id'],
                               "conclusion": alert_msg + conclusion}]
    else:
        execute_conclusion= llm_conclusion

    return execute_conclusion


def main():
    """主入口：从 stdin 或文件读取输入 JSON，执行并输出结果。"""
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
    if args.input_file:
        # 默认从input.json读取输入
        with open(args.input_file, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    else:
        raise Exception("没有有效输入，无法执行行动反馈")

    action_res = input_data.get("action_res", [])
    action_basics = input_data.get("action_basics", [])
    alert_info = input_data.get("alertInfo", None)

    execute_conclusion = asyncio.run(run(action_res, action_basics, alert_info))
    
    # 将输出保存到output.json
    input_data.update({"execute_conclusion":execute_conclusion})
    result= input_data
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info("输出已保存到output.json")
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

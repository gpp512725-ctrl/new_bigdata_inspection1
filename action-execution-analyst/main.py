import json
import logging
import sys
import argparse
import os
from datetime import datetime

from scripts.orchestrator import ActionExecutionAnalyst

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """主入口：从文件读取 input_path，执行三步流程，输出最终结果"""
    parser = argparse.ArgumentParser(
        description="行动执行分析员 - 串联 param-enrichment → action_execution → result_feedback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input-file", 
        help="输入 JSON 文件路径（包含 input_path）", 
        # default="test_input_v1.json"
    )
    parser.add_argument(
        "--input", type=str, help="自定义输入数据 (JSON 字符串)"
    )
    parser.add_argument(
        "-o", "--output-file", 
        help="输出 JSON 文件路径", 
        default="output.json"
    )

    args = parser.parse_args()
    
    if not args.input_file and args.input:
        with open("user_input.json", "w", encoding="utf-8") as f:
            input = json.loads(args.input)
            json.dump(input, f, ensure_ascii=False, indent=2)
        args.input_file="user_input.json"
    
    
    logger.info("开始执行行动执行分析流程")
    logger.info("输入路径：%s", args.input_file)
    
    # 创建编排器并执行
    analyst = ActionExecutionAnalyst()
    result = analyst.run(args.input_file, args.output_file)
    
    # 输出结果
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info("执行完成，结果已保存到：%s", args.output_file)
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

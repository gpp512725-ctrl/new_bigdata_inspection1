import json
import logging
import subprocess
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent

# 依赖技能路径配置
# SKILL_PATHS = {
#     "param_enrichment": Path(r"C:\Users\wulang\.openclaw\workspace\skills\param-enrichment"),
#     "action_execution": Path(r"C:\Users\wulang\.openclaw\workspace\skills\action_execution"),
#     "result_feedback": Path(r"C:\Users\wulang\.openclaw\workspace\skills\result_feedback"),
# }

SKILL_PATHS = {
    "param_enrichment": Path(os.path.join(SKILLS_DIR,r"param-enrichment")),
    "action_execution":  Path(os.path.join(SKILLS_DIR,r"action_execution")),
    "result_feedback":  Path(os.path.join(SKILLS_DIR,r"result_feedback")),
}


class ActionExecutionAnalyst:
    """行动执行分析员编排器
    
    负责串联三个技能：
    1. param-enrichment: 参数补充，输出 actions
    2. action_execution: 执行行动，输出 action_res
    3. result_feedback: 生成修复结论，输出 execute_conclusion
    """
    
    def __init__(self):
        self.temp_dir = Path(__file__).parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def _run_skill(self, skill_name: str, input_file: str, output_file: str) -> bool:
        """执行指定技能
        
        Args:
            skill_name: 技能名称 (param_enrichment, action_execution, result_feedback)
            input_file: 输入文件路径
            output_file: 输出文件路径
            
        Returns:
            执行是否成功
        """
        skill_path = SKILL_PATHS.get(skill_name)
        if not skill_path:
            logger.error("未知技能：%s", skill_name)
            return False
        
        main_py = skill_path / "main.py"
        if not main_py.exists():
            logger.error("技能主文件不存在：%s", main_py)
            return False
        
        cmd = [
            "python",
            str(main_py),
            "-i", input_file,
            "-o", output_file
        ]
        
        logger.info("执行技能：%s", skill_name)
        logger.info("命令：%s", " ".join(cmd))
        
        try:
            result = subprocess.run(
                cmd,
                # capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
                encoding="utf-8"
            )
            
            # result = subprocess.run(
            #     [sys.executable, str(char_script), "--input_path", input_path, "--output_path", char_output],
            #     # capture_output=True,
            #     text=True,
            #     encoding="utf-8",
            #     cwd=str(INSPECTION_CHAR_DIR),
            #     timeout=300
            # )
            
            if result.returncode != 0:
                logger.error("技能执行失败：%s", result.stderr)
                return False
            
            logger.info("技能执行成功：%s", skill_name)
            if result.stdout:
                logger.debug("输出：%s", result.stdout)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("技能执行超时：%s", skill_name)
            return False
        except Exception as e:
            logger.error("技能执行异常：%s - %s", skill_name, str(e))
            return False
    
    def run(self, input_path: str, final_output_path: str) -> dict:
        """执行完整的行动执行分析流程
        
        Args:
            input_path: 原始行动信息文件路径
            final_output_path: 最终输出文件路径
            
        Returns:
            包含 execute_conclusion 和中间输出的结果字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 定义中间文件路径
        param_enrichment_output = self.temp_dir / f"param_enrichment_{timestamp}.json"
        action_execution_output = self.temp_dir / f"action_execution_{timestamp}.json"
        
        result = {
            "execute_conclusion": None,
            "success": False,
            "error": None,
            "intermediate_outputs": {
                "param_enrichment_output": str(param_enrichment_output),
                "action_execution_output": str(action_execution_output),
            }
        }
        
        # 步骤 1: 调用 param-enrichment
        logger.info("=" * 60)
        logger.info("步骤 1: 调用 param-enrichment 进行参数补充")
        logger.info("=" * 60)
        
        if not self._run_skill("param_enrichment", input_path, str(param_enrichment_output)):
            result["error"] = "param-enrichment 执行失败"
            return result
        
        # 读取 param-enrichment 输出，提取 actions
        try:
            with open(param_enrichment_output, "r", encoding="utf-8") as f:
                param_data = json.load(f)
            actions = param_data.get("actions", [])
            if not actions:
                result["error"] = "param-enrichment 输出中未找到 actions"
                return result
            logger.info("参数补充完成，共 %d 个行动", len(actions))
        except Exception as e:
            result["error"] = f"读取 param-enrichment 输出失败：{str(e)}"
            return result
        
        # 步骤 2: 调用 action_execution
        logger.info("=" * 60)
        logger.info("步骤 2: 调用 action_execution 执行行动")
        logger.info("=" * 60)
        
        if not self._run_skill("action_execution", str(param_enrichment_output), str(action_execution_output)):
            result["error"] = "action_execution 执行失败"
            return result
        
        # 读取 action_execution 输出
        try:
            with open(action_execution_output, "r", encoding="utf-8") as f:
                action_data = json.load(f)
            action_res = action_data.get("action_res", [])
            logger.info("行动执行完成，共 %d 个结果", len(action_res))
        except Exception as e:
            result["error"] = f"读取 action_execution 输出失败：{str(e)}"
            return result
        
        # 步骤 3: 调用 result_feedback
        logger.info("=" * 60)
        logger.info("步骤 3: 调用 result_feedback 生成修复结论")
        logger.info("=" * 60)
        
        result_feedback_output = self.temp_dir / f"result_feedback_{timestamp}.json"
        
        if not self._run_skill("result_feedback", str(action_execution_output), str(result_feedback_output)):
            result["error"] = "result_feedback 执行失败"
            return result
        
        # 读取最终结果
        try:
            with open(result_feedback_output, "r", encoding="utf-8") as f:
                final_data = json.load(f)
            execute_conclusion = final_data.get("execute_conclusion", [])
            
            # 格式化结论为字符串
            if isinstance(execute_conclusion, list):
                conclusion_text = "\n\n".join(
                    [item.get("conclusion", "") for item in execute_conclusion]
                )
            else:
                conclusion_text = str(execute_conclusion)
            
            result["execute_conclusion"] = conclusion_text
            result["success"] = True
            result["intermediate_outputs"]["result_feedback_output"] = str(result_feedback_output)
            
            logger.info("修复结论生成完成")
            
        except Exception as e:
            result["error"] = f"读取 result_feedback 输出失败：{str(e)}"
            return result
        
        return result

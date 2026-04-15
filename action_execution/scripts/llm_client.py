import json
import logging
from openai import OpenAI

from scripts.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端类，用于调用LLM生成文案"""
    
    def __init__(self):
        """初始化LLM客户端"""
        self.llm = config.LLM
        self.llm_prompt = config.LLM_PROMPT
    
    def generate_failure_message(self, action: dict, error_info: str,alert_info:dict) -> str:
        """调用 LLM 生成执行失败的描述文案。

        Args:
            action: 行动对象，包含 tool_name_cn, tool_name_en, action_des 等。
            error_info: MCP 执行返回的错误信息。

        Returns:
            LLM 生成的失败描述文案字符串。
        """
        try:
            # 调用真实的大模型API
            client = OpenAI(
                api_key=self.llm['api_key'],
                base_url=self.llm['api_base']
            )
            
            response = client.chat.completions.create(
                model=self.llm['model'],
                messages=[
                    {"role": "system", "content":self.llm_prompt },
                    {"role": "user", "content": f"操作失败的具体原因：{error_info}\n执行的动作信息{action}\n当前故障{alert_info}"}
                ],
                temperature=self.llm['temperature'],
                max_tokens=self.llm['max_tokens'],
                # response_format={"type":"json_object"},
                extra_body={"chat_template_kwargs":{"enable_thinking":False}}
            )
            
            # 解析大模型返回的结果
            result = response.choices[0].message.content
            return result
        except Exception as exc:
            logger.error("LLM 调用失败: %s", exc)
            raise Exception("llm运行失败")

# 导出LLM客户端实例
llm_client = LLMClient()

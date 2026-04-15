"""步骤 8：调用 LLM 生成自然语言修复结论。"""

import json
import logging
import requests
from openai import OpenAI

from scripts.config import LLM_CONFIG,LLM_PROMPT

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端类"""
    
    @staticmethod
    def generate_conclusion(check_info: list[dict]) -> str:
        """调用 LLM，用自然语言总结修复结果。

        Args:
            check_info: 整合的全部特征执行结果。

        Returns:
            LLM 生成的自然语言修复结论。
        """
        # 直接返回降级结果，跳过API调用

        logging.info("开始使用真实大模型API分析执行结果")
        
               
        # 调用真实的大模型API
        client = OpenAI(
            api_key=LLM_CONFIG['api_key'],
            base_url=LLM_CONFIG['api_base']
        )
        
        response = client.chat.completions.create(
            model=LLM_CONFIG['model'],
            messages=[
                {"role": "system", "content":LLM_PROMPT },
                {"role": "user", "content": f"行动执行结果:{check_info}"}
            ],
            temperature=LLM_CONFIG['temperature'],
            max_tokens=LLM_CONFIG['max_tokens'],
            response_format={"type":"json_object"},
            extra_body={"chat_template_kwargs":{"enable_thinking":False}}
        )
        
        # 解析大模型返回的结果
        result = json.loads(response.choices[0].message.content)
        logging.info("真实大模型API分析完成")
        return result

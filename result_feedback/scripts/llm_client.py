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
        logging.info("开始使用 Anthropic API 分析执行结果")

        token_path = "/home/claude/.claude/remote/.oauth_token"
        with open(token_path, "r", encoding="utf-8") as tf:
            anthropic_key = tf.read().strip()

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": LLM_CONFIG.get('max_tokens', 4000),
                "system": LLM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": f"行动执行结果:{check_info}\n\n请仅输出符合要求的 JSON，不要包含任何额外解释或代码围栏。",
                    }
                ],
            },
            timeout=LLM_CONFIG.get('timeout', 300),
        )
        resp.raise_for_status()
        data = resp.json()
        response_text = data["content"][0]["text"].strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```", 2)[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        result = json.loads(response_text)
        logging.info("Anthropic API 分析完成")
        return result

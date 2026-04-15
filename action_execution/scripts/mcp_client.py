import json
import logging
import requests
import random
from datetime import datetime, timezone, timedelta

from scripts.config import config

logger = logging.getLogger(__name__)

# 东八区时区
CST = timezone(timedelta(hours=8))


class MCPClient:
    """MCP客户端类，用于调用MCP工具执行行动"""

    def __init__(self):
        """初始化MCP客户端"""
        self.config = config.MCP

    def build_query(self, action: dict) -> str:
        """根据 action 构造 MCP 工具执行的 query 描述。"""
        tool_name_en = action["tool_name_en"]
        tool_name_cn = action["tool_name_cn"]
        data = action["data"]
        return (
            f"行动执行，执行工具为{tool_name_en}，即{tool_name_cn}，"
            f"tool工具参数（data）为:{json.dumps(data, ensure_ascii=False)}"
        )

    @staticmethod
    def generate_mock_mcp_result(tool_name_en, tool_name_cn):
        # 随机决定成功或失败
        is_success = random.choice([True, False])
        # is_success = random.choice([False])

        if is_success:
            code = 200
            msg = "操作成功"
        else:
            # 随机失败 code
            code = random.choice([400, 403, 500])
            msg = "操作失败"

        execute_content = json.dumps({"code": code, "msg": msg}, ensure_ascii=False)

        return {
            "tool_name": tool_name_en,
            "tool_describe": tool_name_cn,
            "execute_content": execute_content,
        }

    def call_mcp_tool(self, action: dict) -> dict:
        """调用 MCP 工具执行单个行动，返回原始响应结果。

        返回:
            dict: 包含 status_code, body(dict), error(str|None), execute_time
        """
        query = self.build_query(action)
        logger.info("MCP query: %s", query)

        # 模拟MCP服务调用结果
        # 实际环境中，这里会调用真实的MCP服务
        result = MCPClient.generate_mock_mcp_result(
            action["tool_name_en"], action["tool_name_cn"]
        )
        logger.info("MCP 调用结果: %s", json.dumps(result, ensure_ascii=False))
        return result

        # 以下是实际调用MCP服务的代码，暂时注释掉
        """
        payload = {
            "tool_name": action["tool_name_en"],
            "data": action["data"],
            "query": query,
        }

        try:
            resp = requests.post(
                self.config["url"],
                json=payload,
                timeout=self.config["timeout"],
                headers={"Content-Type": "application/json"},
            )
            body = resp.json() if resp.text else {}
            return {
                "status_code": resp.status_code,
                "body": body,
                "error": None,
                "execute_time": execute_time,
            }
        except requests.RequestException as exc:
            logger.error("MCP 调用异常: %s", exc)
            return {
                "status_code": -1,
                "body": {},
                "error": str(exc),
                "execute_time": execute_time,
            }
        """


# 导出MCP客户端实例
mcp_client = MCPClient()

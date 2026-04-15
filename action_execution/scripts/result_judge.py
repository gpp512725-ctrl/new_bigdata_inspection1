import json


class ResultJudge:
    """结果判断类，用于判断MCP工具执行是否成功"""

    @staticmethod
    def is_success(mcp_result: dict) -> bool:
        """判断 MCP 工具是否执行成功。

        满足以下任一条件即视为成功:
        1. HTTP 状态码为 200
        2. 返回 body 中 code 字段等于 200
        3. 返回信息中包含 "操作成功"
        4. 返回信息中包含 "success"（不区分大小写）
        """
        # 条件 1: HTTP 状态码 200
        execute_content = mcp_result["execute_content"]
        execute_content = json.loads(execute_content)
        if execute_content.get("code") == 200:
            return True

        # 条件 3 & 4: 在整个 body 文本中搜索关键词
        body_text = json.dumps(execute_content, ensure_ascii=False).lower()
        if "操作成功" in body_text or "success" in body_text:
            return True

        return False


# 导出结果判断实例
result_judge = ResultJudge()

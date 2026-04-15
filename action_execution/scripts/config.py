class Config:
    """配置类，包含所有静态配置信息"""
    # MCP Server 配置
    MCP = {
        "server_name": "行动执行",
        "type": "streamable_http",
        "url": "http://192.168.10.55:8001/mcp",
        "timeout": 30,
    }

    # LLM 配置
    LLM = {
            "api_key": "sk-18d889d62ad74d60875b2fd8dd88f254",  # 大模型API密钥
            "model": "qwen3.5-plus",  # 模型名称
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # API基础URL
            "temperature": 0.3,  # 温度参数
            "max_tokens": 2000  # 最大 token 数
        }

    # 文件路径配置
    FILES = {
        "input": "input.json",
        "output": "output.json",
    }
    
    LLM_PROMPT="""
角色
你是一个大数据运维场景的专业客服，能够将机器无法处理的流程，或处理失败的流程，形成专业话术，向用户解释失败情况，并提供清晰的人工操作建议，以安抚用户，帮助用户快速明确行动方向。
技能
技能1：操作失败解释
1. 明确告知用户是哪个action操作失败，从mcp_output-action_name中获取，并简单致歉，句式：抱歉，非人工Ixxx动作执行失败（已多次重试）。
2. 能够快速理解执行的动作信息actions和操作失败的具体信息是mcp_output，如能够从中获取失败的原因，请提供具体原因给用户；如无法获取，则进行人工操作指引。句式：失败原因有1，2，3...依次类推。
技能2：人工操作指引
1. 提出操作失败可能的原因，句式：无法定位失败原因，可能原因有1，2，3...依次类推。
2. 提示用户可能原因，进行人工排查与纠正。
限制
1. 语言简明、通俗、口语化，非必要时不使用过于专业术语。
2. 仅围绕动作执行的失败的输出相关话术与指引。
3. 输出内容与格式，严格按照要求来。
4. -- Don't use json markdown format
                """

# 导出配置实例
config = Config()

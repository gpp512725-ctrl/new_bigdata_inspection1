#!/usr/bin/env python3
"""
Configuration for param-enrichment skill

This file contains all configurable parameters for the skill,
including API endpoints, LLM prompts, and default values.
"""

# MCP API Configuration - Updated for aiohttp with enabled flag
MCP_API_CONFIG = {
    "login": {
        "url": "http://192.168.10.54:8020/api/privilege/user/login",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json"
        },
        "timeout": 100,
        "enabled": True,  # 默认启用，设为False使用mock数据
        "team_id":71
    },
    "tool_args": {
        "url": "http://192.168.54:8020/api/mcp/pageQueryList",
        "method": "GET",
        "headers": {
            "Content-Type": "application/json"
        },
        "timeout": 100,
        "enabled": True  # 默认启用，设为False使用mock数据
    }
}

# Default credentials (will be overridden by environment variables)
MCP_CREDENTIALS = {
    "username": "wulang",
    "password": "UHhzZW1pMjAyNA==",
    "app_id": "1"
}

TOOL_PARAMS={
    "server_name":"行动执行MCP",
    "creator":0,
    "sort":1,
    "page":1,
    "size":1,
    "need_tools":1,
}


# LLM Configuration
LLM_CONFIG = {
    "api_key": "sk-18d889d62ad74d60875b2fd8dd88f254",   # Default value, will be overridden by environment variables
    "model": "qwen3.5-plus",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature":0.1,
    "max_tokens": 20000,
    "timeout": 300,   # Request timeout in seconds
}

# LLM System Prompt for parameter filling
LLM_SYSTEM_PROMPT = """#角色
你是一个专业的数据整合专家，能够根据工具入参要求，查找合适的参数值，填充在对应参数字段中。

##技能
###技能1：理解参数要求
1.读取action参数信息'params',包含参数名title,参数描述description,参数类型type,参默认值default。

###技能2：填充参数值
1.填充各个参数名title对应的参数值。如有参数默认值default,那么参数值直接填写默认值；如果没有参数默认值default,那么需要深度理解故障信息'alterInfo'和参数描述description,并在此基础上提取参数值进行填充。
2.填充后请严格按照以下示例格式输出：
{"actions":[
    {
        "data":{
            "ip:"192.168.10.180",
            "serviceRole":"hdfs",
            "commandType":"restart"},
        "tool_name_cn":"重启HDFS服务",
        "tool_name_en":"hdfs_restart",
        "action_des":"",
        "feature_code":"",
        "instance_id":"",
        "action_priority":""
    },
    {
        "data":{
            "configFile:"",
            "fieldName":"",
            "targetValue":""},
        "tool_name_cn":"",
        "tool_name_en":"",
        "action_des":"",
        "feature_code":"",
        "instance_id":"",
        "action_priority":""
    }
]}

##限制
- 仅围绕参数信息和故障信息填充参数值，不涉及其他无关话题。
- 输出格式要严格按照示例要求来输出。
- Don't use “'''json” markdown format
"""

# Entity to ServiceRole mapping for rule-based fallback
ENTITY_SERVICEROLE_MAP = {
    "namenode": "NAMENODE",
    "datanode": "DATANODE",
}

# Action tag values
ACTION_TAG_HUMAN = "human"  # Manual execution required
ACTION_TAG_AUTO = ""        # Automatic execution allowed

# Mock data for disabled APIs
MOCK_TOOL_ARGS = [
            {
                "name": "hdfs_restart",
                "input_args_detail": {
                    "data": {
                        "type": "object",
                        "title": "data",
                        "required": ["ip", "actionName"],
                        "properties": {
                            "ip": {
                                "type": "string",
                                "title": "Ip",
                                "description": "ip地址，例如：192.168.1.10",
                            },
                            "actionName": {
                                "type": "string",
                                "title": "Actionname",
                                "description": "action名称，例如：重启HDFS服务",
                            },
                            "commandType": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Commandtype",
                                "default": "restart",
                                "description": "命令类型，例如：restart",
                            },
                            "serviceRole": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Servicerole",
                                "default": "NameNode",
                                "description": "服务角色，例如：DataNode",
                            },
                        },
                    },
                    "description": "json结构体，包含ip, serviceRole, commandType",
                },
            },
            {
                "name": "namenode_heap_memory_expand",
                "input_args_detail": {
                    "value": {
                        "type": "string",
                        "title": "value",
                        "description": "SimpleServiceConfig的固定字符串参数，值范围例如：4",
                    }
                },
            },
            {
                "name": "datanode_heap_memory_expand",
                "input_args_detail": {
                    "value": {
                        "type": "string",
                        "title": "value",
                        "description": "SimpleServiceConfig的固定字符串参数，值范围例如：4",
                    }
                },
            },
        ]
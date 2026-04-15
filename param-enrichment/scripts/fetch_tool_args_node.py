#!/usr/bin/env python3
"""
步骤2 & 3：拉取工具入参定义（使用aiohttp异步客户端）
"""

import os
import asyncio
from socket import timeout
import aiohttp
from typing import Optional, Tuple, List, Dict, Any
from scripts.config import MCP_API_CONFIG, MCP_CREDENTIALS, TOOL_PARAMS,MOCK_TOOL_ARGS


class FetchToolArgsNode:
    """
    负责获取工具入参定义的节点，使用aiohttp实现异步API调用
    """

    def __init__(self) -> None:
        self.tool_params = TOOL_PARAMS

    @staticmethod
    async def get_auth_token(api_config: dict) -> tuple:
        """
        调用 get_token API 获取认证信息
        返回 (authorization, team_id) 元组，失败时返回 (None, None)
        """
        # 从配置直接获取凭证
        token_config = api_config.get("login", {})
        team_id = str(token_config.get("team_id"))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=token_config.get("method", "POST"),
                    url=token_config.get("url"),
                    json={
                        "username": MCP_CREDENTIALS["username"],
                        "password": MCP_CREDENTIALS["password"],
                        "app_id": int(MCP_CREDENTIALS["app_id"]),
                    },
                    headers=token_config.get("headers"),
                    timeout=aiohttp.ClientTimeout(total=token_config.get("timeout")),
                ) as response:
                    if response.status != 200:
                        raise Exception("token API 调用失败")
                    api_response = await response.json()
                    refresh_token_type = api_response.get("data").get(
                        "refresh_token_type"
                    )
                    refresh_token = api_response.get("data").get("refresh_token")
                    authorization = refresh_token_type + " " + refresh_token
                    teams = api_response.get("data").get("user").get("teams")
                    if token_config.get("team_id") not in teams:
                        team_id = str(teams[0])
                    return authorization, team_id
        except Exception as e:
            print(f"  [警告] 获取 token 异常：{e}")

        return None, team_id

    @staticmethod
    async def fetch_tool_args(api_config: dict) -> list:
        """
        调用 API 获取工具的入参定义列表。
        步骤：
        1. 调用 get_token API 获取认证信息
        2. 调用 mcp_get_service_params API 获取工具入参
        3. 解析返回的工具入参信息
        返回 input_args 列表，每项含 name / type / default / description。
        失败时返回空列表。
        """
        # 检查API是否启用
        tool_args_config = api_config.get("tool_args", {})
        enabled = tool_args_config.get("enabled", True)

        if not enabled:
            print(f"  [模拟] 工具参数API已禁用，使用mock数据")

        # 1. 获取认证信息
        authorization, team_id = await FetchToolArgsNode.get_auth_token(api_config)
        if not authorization or not team_id:
            print(f"  [警告] 获取认证信息失败")

        # 2. 调用 mcp_get_service_params API
        import copy

        params = copy.deepcopy(TOOL_PARAMS)
        params.update({"team_id": team_id})
        headers = tool_args_config.get("headers")
        headers.update({"authorization": authorization})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    tool_args_config.get("url"), params=params, headers=headers
                ) as response:
                    if response.status != 200:
                        raise Exception("参数补充 API 调用失败")
                    api_response = await response.json()
                    return api_response.get("data").get("items")[0].get("tools")

        except Exception as e:
            print(f"  [警告] API 请求异常：{e}")

        return []

    @staticmethod
    async def batch_fetch_tool_args(tool_names: list, api_config: dict) -> dict:
        """
        批量获取多个工具的入参定义，去重后请求。
        返回 {tool_name_en: [input_args]} 字典。
        """
        # 验证必需字段（仅当API启用时）
        login_enabled = api_config.get("login", {}).get("enabled", True)
        tool_args_enabled = api_config.get("tool_args", {}).get("enabled", True)

        if login_enabled or tool_args_enabled:
            username = MCP_CREDENTIALS["username"]
            password = MCP_CREDENTIALS["password"]
            app_id = MCP_CREDENTIALS["app_id"]

            if not all([username, password, app_id]):
                missing = []
                if not username:
                    missing.append("username")
                if not password:
                    missing.append("password")
                if not app_id:
                    missing.append("app_id")
                print(
                    f"[错误] 缺少必需的MCP API配置: {', '.join(missing)}",
                    file=sys.stderr,
                )
                return {}

        unique_tools = list(dict.fromkeys(tool_names))  # 去重保序

        print(f"\n[API] 开始获取 {len(unique_tools)} 个工具的入参定义...")

        tool_args_map = await FetchToolArgsNode.fetch_tool_args(api_config)
        
        if not tool_args_map:
            tool_args_map= MOCK_TOOL_ARGS

        return tool_args_map, unique_tools

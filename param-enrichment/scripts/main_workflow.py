#!/usr/bin/env python3
"""
主工作流：整合所有节点，执行完整的参数填充流程
"""

import asyncio
import json
from scripts.load_data_node import LoadDataNode
from scripts.fetch_tool_args_node import FetchToolArgsNode
from scripts.fill_params_node import FillParamsNode
from scripts.config import MCP_API_CONFIG


class MainWorkflow:
    """
    主工作流类，协调各个节点完成参数填充任务
    """

    @staticmethod
    async def run(report: dict) -> dict:
        """
        执行完整的参数填充工作流
        
        Args:
            report: 输入的巡检分析报告字典
            
        Returns:
            包含填充后actions的字典
        """
        print("[步骤1] 加载基础数据...")
        action_basics = LoadDataNode.load_action_basics(report)
        abnormal_instances = LoadDataNode.load_abnormal_instances(report)
        alert_info = LoadDataNode.load_alert_info(report)
        action_names = LoadDataNode.load_action_names(report)
        
        # 为action_basics添加内部字段用于参数填充
        for ab in action_basics:
            # 找到对应的abnormal_instance
            entity = ab.get("entity", "")
            for ai in abnormal_instances:
                if ai.get("entity") == entity:
                    ab["_entity"] = entity
                    ab["_current_value"] = ai.get("current_value")
                    ab["extra_info"] = ai.get("extra_info", {})
                    break
        
        print(f"[步骤2&3] 获取 {len(action_names)} 个工具的入参定义...")
        tool_args_map = await FetchToolArgsNode.batch_fetch_tool_args(
            action_names, 
            MCP_API_CONFIG
        )
        
        print("[步骤4&5] 填充参数并构建actions...")
        actions = FillParamsNode.build_actions(
            action_basics,
            tool_args_map,
            alert_info
        )
        
        return {"actions": actions}
#!/usr/bin/env python3
"""
步骤1：加载基础数据
"""

class LoadDataNode:
    """
    负责从输入报告中提取 actionBasics 和 abnormalInstances 的节点
    """

    @staticmethod
    def load_action_basics(report: dict) -> list:
        """
        从报告中提取 actionBasics 数组
        """
        return report.get("actionBasics", [])

    @staticmethod
    def load_abnormal_instances(report: dict) -> list:
        """
        从报告中提取 abnormalInstances 数组
        """
        return report.get("abnormalInstances", [])

    @staticmethod
    def load_alert_info(report: dict) -> dict:
        """
        从报告中提取 alertInfo 对象
        """
        return report.get("alertInfo", {})

    @staticmethod
    def load_action_names(report: dict) -> list:
        """
        从报告中提取 action_names 数组
        """
        return report.get("action_names", [])
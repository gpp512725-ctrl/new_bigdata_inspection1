from collections import defaultdict
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import asyncio
import aiohttp
import logging
from .config import ABNORMAL_DETECTION_API, ALARM_PROB_LIMIT, KEEP_DETAIL_RATIO

logger = logging.getLogger(__name__)

class AbnormalJudgment:
    """异常判断节点"""

    def __init__(self):
        self.abnormal_detection_api = ABNORMAL_DETECTION_API
        self.alarm_prob_limit = ALARM_PROB_LIMIT
        self.keep_detail_ratio = KEEP_DETAIL_RATIO

    async def call_abnormal_judgment_api(
        self,
        api_inputs: List[Dict[str, Any]],
        entity_instances: List[Any],
        process_enable=True,
    ) -> List:
        """调用异常判断API"""
        try:
            if not api_inputs or not isinstance(api_inputs, list):
                raise ValueError("API输入数据必须是数组")

            # 检查是否启用真实API调用
            api_config = self.abnormal_detection_api
            api_inputs = {
                "featureInfos": api_inputs,
                "alert_detail_flag": True,
            }
            results = []
            if api_config.get("enabled", False):
                results = await self._call_real_api(api_inputs, api_config)
                results = results["data"]["abnormalInfo"]
            else:
                # 使用mock数据（保持原始逻辑）
                # results = []
                # for input_data in api_inputs:
                #     result = await self._process_single_input(input_data)
                #     results.append(result)
                results = self.generate_mock_feature_infos(api_inputs)
                logger.info(f"Processed {len(results)} judgment results (mock mode)")
            if process_enable:
                return self._parse_api_response(results, entity_instances)
            else:
                return results

        except Exception as e:
            raise Exception(f"Abnormal judgment API call failed: {str(e)}")

    async def _call_real_api(
        self, api_inputs: List[Dict[str, Any]], api_config: Dict[str, Any]
    ) -> List:
        """调用真实的异常检测API"""
        url = api_config.get("url")
        method = api_config.get("method", "POST")
        headers = api_config.get("headers", {})
        timeout = api_config.get("timeout", 30)

        if not url:
            raise ValueError("API URL is required when real API is enabled")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=api_inputs,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status != 200:
                        raise Exception(
                            f"API returned status {response.status}: {await response.text()}"
                        )

                    api_response = await response.json()
                    return api_response

        except Exception as e:
            raise Exception(f"Real API call failed: {str(e)}")

    def _parse_api_response(
        self, api_response: Any, entity_instances: List[Any]
    ) -> List:
        """解析真实API的响应并转换为JudgmentResult对象"""
        abnormalInfo = api_response
        instance_info = [
            {"instance_id": instance.instance_id, "ip": instance.ip}
            for instance in entity_instances
        ]
        for i in abnormalInfo:
            for j in instance_info:
                if i["instance_id"] == j["instance_id"]:
                    i["ip"] = j["ip"]
        data = list()
        feature_limit = []
        feature_limit_code = []
        abnormalInstances = []

        for item in abnormalInfo:
            all_detail = []
            # 获取特征上下限
            if item["feature_code"] not in feature_limit_code:
                feature_limit_code.append(item["feature_code"])
                feture_code_info = {
                    "feature_code": item["feature_code"],
                    "compute_upper_bound": item["compute_upper_bound"],
                    "compute_lower_bound": item["compute_lower_bound"],
                }
                feature_limit.append(feture_code_info)

            # 根据阈值先删除一些不必要的数据
            for detail in item["all_detail"]:
                prob = detail["probability"]
                if prob > self.alarm_prob_limit:
                    alarm_prob = f"{round(prob*100)}%"
                    detail.update({"alarm_prob": alarm_prob})
                    all_detail.append(detail)
            # 无高概率数据跳过
            if not all_detail:
                continue

            # 创建一个字典，用于按type分租
            grouped = defaultdict(list)
            for cur_detail in all_detail:
                grouped[cur_detail["type"]].append(cur_detail)

            sorted_grouped = {
                type_key: sorted(
                    type_items, key=lambda x: x["probability"], reverse=True
                )
                for type_key, type_items in grouped.items()
            }

            # 取数据保存
            keep_details = []
            for type_name, group in sorted_grouped.items():
                count = round(len(group) * self.keep_detail_ratio) + 1
                keep_detail = group[:count]
                keep_details.extend(keep_detail)
            if keep_details:
                alarm_data = {
                    k: v
                    for k, v in item.items()
                    if k not in ["all_detail", "detail", "detail_range"]
                }
                alarm_data.update({"detail": keep_detail})
                data.append(alarm_data)
            abnormalInstance = {
                "entity_name": item["entity_name"],
                "instance_id": item["instance_id"],
                "feature_code": item["feature_code"],
                "ip": item["ip"],
            }
            abnormalInstances.append(abnormalInstance)
        is_alarm = True if data else False
        if not is_alarm:
            data.append({})
        results = {
            "abnormalInfo": data,
            "is_alarm": is_alarm,
            "feature_limit": feature_limit,
            "abnormalInstances": abnormalInstances,
        }
        return results

    def generate_mock_feature_infos(self, input_data):
        """根据 featureInfos 生成带 mock 字段的结果"""

        def random_ip():
            return ".".join(str(random.randint(1, 254)) for _ in range(4))

        def random_value():
            return round(random.uniform(0, 100), 2)

        def random_type():
            return random.choice(["正常", "报警", "突增"])

        def random_probability():
            return round(random.uniform(0, 1), 2)

        def gen_all_detail(start_time, end_time, points=5):
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            delta = (end - start) / points

            details = []
            for i in range(points):
                ts = start + delta * i
                prob = random_probability()
                details.append(
                    {
                        "values": random_value(),
                        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                        "type": random_type(),
                        "probability": prob,
                        "alarm_prob": f"{int(prob * 100)}%",
                    }
                )
            return details

        result = []

        for item in input_data.get("featureInfos", []):
            lower = round(random.uniform(0, 20), 2)
            upper = round(random.uniform(80, 100), 2)

            result.append(
                {
                    # "entity_name": item["entity_name"],
                    "instance_id": item["instance_id"],
                    "feature_code": item["feature_code"],
                    # 新增字段
                    # "ip": random_ip(),
                    "result": random.choice([True, False]),
                    "compute_lower_bound": lower,
                    "compute_upper_bound": upper,
                    "all_detail": gen_all_detail(item["start_time"], item["timestamp"]),
                }
            )

        return result

    def analyze_results(self, judgment_results: List) -> Dict[str, Any]:
        """分析结果并生成摘要"""
        summary = {
            "total_inspections": len(judgment_results),
            "anomalies_found": 0,
            "entities_with_anomalies": set(),
            "features_with_anomalies": set(),
            "anomaly_details": [],
            "statistics": {
                "average_probability": 0.0,
                "max_probability": 0.0,
                "anomaly_rate": 0.0,
            },
        }

        total_probability = 0.0
        max_probability = 0.0

        for result in judgment_results:
            if result.has_anomalies:
                summary["anomalies_found"] += 1
                summary["entities_with_anomalies"].add(result.entity_name)
                summary["features_with_anomalies"].add(result.feature_code)

                # 收集异常详情
                for detail in result.all_detail:
                    if detail.type != "normal" or detail.probability > 0.7:
                        summary["anomaly_details"].append(
                            {
                                "entity_name": result.entity_name,
                                "feature_code": result.feature_code,
                                "type": detail.type,
                                "value": detail.value,
                                "probability": detail.probability,
                                "timestamp": detail.timestamp,
                            }
                        )

            # 计算概率统计
            avg_prob = sum(detail.probability for detail in result.all_detail) / len(
                result.all_detail
            )
            total_probability += avg_prob
            max_probability = max(
                max_probability, max(detail.probability for detail in result.all_detail)
            )

        # 计算总体统计
        summary["statistics"]["average_probability"] = (
            total_probability / len(judgment_results) if judgment_results else 0.0
        )
        summary["statistics"]["max_probability"] = max_probability
        summary["statistics"]["anomaly_rate"] = (
            summary["anomalies_found"] / len(judgment_results)
            if judgment_results
            else 0.0
        )

        # 转换set为list
        summary["entities_with_anomalies"] = list(summary["entities_with_anomalies"])
        summary["features_with_anomalies"] = list(summary["features_with_anomalies"])

        return summary

    def get_feature_statistics(self, judgment_results: List) -> Dict[str, Any]:
        """获取特征级别的统计信息"""
        feature_stats = {}

        for result in judgment_results:
            feature_key = f"{result.entity_name}_{result.feature_code}"

            if feature_key not in feature_stats:
                feature_stats[feature_key] = {
                    "entity_name": result.entity_name,
                    "feature_code": result.feature_code,
                    "total_checks": 0,
                    "anomaly_count": 0,
                    "max_probability": 0.0,
                    "average_probability": 0.0,
                    "details": [],
                }

            feature_stat = feature_stats[feature_key]
            feature_stat["total_checks"] += 1

            if result.has_anomalies:
                feature_stat["anomaly_count"] += 1

            # 更新概率统计
            max_prob = max(detail.probability for detail in result.all_detail)
            avg_prob = sum(detail.probability for detail in result.all_detail) / len(
                result.all_detail
            )

            feature_stat["max_probability"] = max(
                feature_stat["max_probability"], max_prob
            )
            feature_stat["average_probability"] = (
                feature_stat["average_probability"] + avg_prob
            ) / 2
            feature_stat["details"].extend(result.all_detail)

        return feature_stats

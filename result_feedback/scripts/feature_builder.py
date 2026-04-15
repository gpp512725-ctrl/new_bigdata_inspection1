"""步骤 3-4：构造 featureInfos 和 alert_feature。"""
import asyncio
import copy
from datetime import datetime, timedelta
from scripts.config import CST, VERIFY_WINDOW_SECONDS


class FeatureBuilder:
    """特征构建类"""
    
    @staticmethod
    def build_feature_infos(action_res_all: list[dict]) -> list[dict]:
        """步骤 3：构造待验证异常特征集合 featureInfos。

        以 (feature_code, instance_id) 为一组唯一值构建数据。
        时间计算规则:
        - 若 (当前时间 - execute_time) >= 120s，timestamp = 当前时间
        - 若 (当前时间 - execute_time) < 120s，timestamp = execute_time + 120s

        Args:
            action_res_all: 全部行动执行结果。

        Returns:
            featureInfos 列表。
        """
        now = datetime.now(CST)

        # 按 (feature_code, instance_id) 分组，取最早的 execute_time
        group: dict[tuple[str, str], str] = {}
        for item in action_res_all:
            key = (item["feature_code"], item["instance_id"])
            et = item["execute_time"]
            if key not in group or et < group[key]:
                group[key] = et

        feature_infos = []
        for (feature_code, instance_id), execute_time in group.items():
            start_time = execute_time
            exec_dt = datetime.fromisoformat(execute_time).replace(tzinfo=CST)
            diff = (now - exec_dt).total_seconds()

            if diff >= VERIFY_WINDOW_SECONDS:
                timestamp = now.isoformat()
            else:
                timestamp = (exec_dt + timedelta(seconds=VERIFY_WINDOW_SECONDS)).isoformat()

            feature_infos.append({
                "start_time": start_time,
                "timestamp": timestamp,
                "instance_id": instance_id,
                "feature_code": feature_code,
            })

        return feature_infos

    @staticmethod
    def build_alert_feature(alert_info: dict | None) -> tuple[bool, dict | None]:
        """步骤 4：构造 alert_feature。

        - alertInfo 为空 → 智能巡检场景，alert_bool=False，alert_feature=None
        - alertInfo 非空 → 故障分析场景，alert_bool=True，alert_feature 从 alertInfo 中获取

        Args:
            alert_info: 告警信息对象。

        Returns:
            (alert_bool, alert_feature):
            - alert_bool=True, alert_feature 从 alertInfo 中提取
            - alert_bool=False, alert_feature=None
        """
        if not alert_info:
            return False, None

        # 故障分析场景：直接从 alertInfo 中获取字段
        alert_feature = {
            "start_time": alert_info.get("start_time", ""),
            "timestamp": alert_info.get("timestamp", ""),
            "instance_id": alert_info.get("instance_id", ""),
            "feature_code": alert_info.get("feature_code", ""),
        }

        return True, alert_feature
    
    @staticmethod
    async def build_all_info(action_basics,action_res,alertInfo):
         # 取得所有未执行的行动
        all_tool_name_cn_list = list(set([item["tool_name_cn"] for item in action_basics]))
        run_tool_name_cn_list = list(set([item["tool_name_cn"] for item in action_res]))
        refuse_actions = list(set(item for item in all_tool_name_cn_list if item not in run_tool_name_cn_list))

        # 根据instance_ids和action进行二次拆分，得到未被采纳（人工和非人工），得到采纳的人工
        action_basics_new = []
        for action in action_basics:
            # 未被采纳的行动，包括人工和非人工
            if action["tool_name_cn"] in refuse_actions:
                extra_info = action["extra_info"]
                for id,i in enumerate(extra_info):
                    if action["tool_name_cn"] == "hdfs_restart" and id > 0:
                        # hdfs_restart只需要一个
                        continue
                ac_new = copy.deepcopy(action)
                del ac_new["extra_info"]
                ac_new.update(i)
                ac_new["code"] = 3 #表示3为未被采纳
                if action["action_tag"] == "human":
                    ac_new["action_msg"] = f'{action["tool_name_cn"]}需人工执行但未被采纳；'
                else:
                    ac_new["action_msg"] = f'{action["tool_name_cn"]}需MCP执行但未执行；'
                action_basics_new.append(ac_new)
            #采纳但是未知是否执行
            elif action["action_tag"] == "human":
                extra_info = action["extra_info"]
                for id, i in enumerate(extra_info):
                    if action["tool_name_en"] == "hdfs_restart" and id > 0:
                        # hdfs_restart只需要重启一次
                        continue
                    ac_new = copy.deepcopy(action)
                    del ac_new["extra_info"]
                    ac_new.update(i)
                    ac_new["code"] = 2  # 表示2为人工执行
                    ac_new["action_msg"] = f'{action["tool_name_cn"]}需人工执行且已被采纳，需要技术人员线下操作'
                    action_basics_new.append(ac_new)

        # 防止间隔时间短没有数据
        # 定义时间格式
        time_format = "%Y-%m-%d %H:%M:%S"
        #找到execute_time最大的项
        latest = max(action_res, key=lambda x: datetime.strptime(x["execute_time"], time_format))
        #输出最大时间值
        max_time = latest["execute_time"]

        # 计算当前时间和最新执行时间的差值
        now = datetime.now()
        cur_time = now.strftime("%Y-%m-%d %H:%M:%S")

        t1 = datetime.strptime(max_time, time_format)
        t2 = datetime.strptime(cur_time, time_format)

        delta = t2 - t1
        delta = int(delta.total_seconds())

        if delta < 120:
            await asyncio.sleep(120 - delta)
            now = datetime.now()
            cur_time = now.strftime("%Y-%m-%d %H:%M:%S")

        # 将人工添加的动作特征加入
        action_res_all = action_res + action_basics_new

        # 构建异常判断入参
        seen = set()
        unique_list = []
        for action_feature_code in action_res_all:
            feature_code = action_feature_code['feature_code']
            instance_id = action_feature_code['instance_id']
            key = (instance_id, feature_code)
            if key not in seen:
                seen.add(key)
                unique_list.append({
                    "start_time": max_time,
                    "timestamp": cur_time,
                    "feature_code": feature_code,
                    "instance_id": instance_id
                })

        # 如果是故障场景，获取故障特征信息
        alert_feature = []
        alert_bool = False
        if alertInfo and "feature_code" in alertInfo and "instance_id" in alertInfo:
            alert_bool = True
            alert_feature.append({
                "start_time": max_time,
                "timestamp": cur_time,
                "feature_code": alertInfo["feature_code"],
                "instance_id": alertInfo["instance_id"]
            })
        else:
            alert_feature = [{}]

        unique_feature = list(set([i["feature_code"] for i in unique_list]))

        ret = {
            "featureInfos": unique_list,
            "alert_feature": alert_feature,
            "alert_bool": alert_bool,
            "action_basics_new": action_basics_new,
            "action_res_all": action_res_all,
            "unique_feature": unique_feature
        }
        return ret 

            

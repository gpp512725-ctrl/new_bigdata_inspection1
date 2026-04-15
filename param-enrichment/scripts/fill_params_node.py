#!/usr/bin/env python3
"""
步骤4 & 5：填充参数，合并输出
"""

import json
import copy
from scripts.config import LLM_SYSTEM_PROMPT, ENTITY_SERVICEROLE_MAP, LLM_CONFIG


class FillParamsNode:
    """
    负责填充参数并合并输出的节点
    """

    # ============================================================
    # 步骤4a：规则引擎填充（LLM 降级兜底）
    # ============================================================
    @staticmethod
    def rule_based_fill(action_basic: dict, input_args: list) -> dict:
        """
        规则引擎：直接映射可确定值的参数，其余使用 default。
        """
        entity = action_basic.get("_entity", "").lower()
        ip = action_basic.get("extra_info", {}).get("ip", "")
        cur_val = action_basic.get("_current_value")

        params = {}
        for arg in input_args:
            name = arg["name"]
            # 使用 config.py 中的默认值作为 fallback
            default = arg.get("default", "")

            if name == "ip":
                params[name] = ip if ip else default
            elif name == "servicerole":
                params[name] = ENTITY_SERVICEROLE_MAP.get(entity, default or "NAMENODE")
            elif name == "commandtype":
                params[name] = default or "restart"
            elif name == "value":
                # 扩容值：当前值 * 1.5，最小 8，返回数字类型
                if cur_val and isinstance(cur_val, (int, float)) and cur_val > 100:
                    new_val = max(8, round(cur_val * 1.5 / 1024))
                    params[name] = new_val  # 返回数字类型
                else:
                    # 尝试将默认值转换为数字
                    if isinstance(default, (int, float)):
                        params[name] = default
                    elif isinstance(default, str):
                        # 尝试从字符串中提取数字
                        try:
                            # 移除单位，只保留数字
                            num_str = "".join(
                                c for c in default if c.isdigit() or c == "."
                            )
                            if num_str:
                                params[name] = (
                                    float(num_str) if "." in num_str else int(num_str)
                                )
                            else:
                                params[name] = 8
                        except:
                            params[name] = 8
                    else:
                        params[name] = 8
            elif name == "limit_bytes_per_sec":
                if cur_val and isinstance(cur_val, (int, float)):
                    limit = max(52428800, int(float(cur_val) * 0.7))
                    params[name] = limit
                else:
                    params[name] = int(default) if default else 83886080
            else:
                # 其余参数：使用默认值
                params[name] = default

        return params

    # ============================================================
    # 步骤4b：LLM 智能填充
    # ============================================================
    @staticmethod
    def llm_fill_params(
        action_basic: dict,
        alert_info: dict,
    ) -> dict:
        """
        调用 LLM 根据告警信息和参数定义智能填充参数值。
        失败时降级到规则引擎。

        llm_config 字段说明：
          api_key    - 阿里云百炼 API Key（必填，否则跳过 LLM）
          base_url   - API 地址，默认 https://dashscope.aliyuncs.com/compatible-mode/v1
          model      - 模型版本，默认 qwen3.5-plus
          max_tokens - 最大输出 token 数（默认 512）
          timeout    - 请求超时秒数（默认 30）
        """
        # 使用传入的 llm_config 中的值，如果不存在则使用 config.py 中的默认值
        api_key = LLM_CONFIG["api_key"]
        base_url = LLM_CONFIG["base_url"]
        model = LLM_CONFIG["model"]
        max_tokens = LLM_CONFIG["max_tokens"]
        timeout = LLM_CONFIG["timeout"]

        if not api_key:
            raise Exception(f"无可用llm")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )

            messages = [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"action参数信息：\n {action_basic}\n故障信息：\n{alert_info}",
                },
            ]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )

            response_text = response.choices[0].message.content
            return json.loads(response_text)

        except Exception as e:
            print(f"    [警告] LLM 填充失败（{e}），降级到规则引擎")
            raise Exception("大模型运行失败")

    @staticmethod
    def add_extra_info(action_basics: list, abnormalInstances: list):
        """
        为action_basics添加实例id和ip
        """
        action_basics_add_info = []
        for action in action_basics:
            action_new = copy.deepcopy(action)
            for abnormal in abnormalInstances:
                if action["feature_code"] == abnormal["feature_code"]:
                    if "extra_info" in action_new:
                        action_new["extra_info"].append(
                            {
                                "instance_id": abnormal["instance_id"],
                                "ip": abnormal["ip"],
                            }
                        )
                    else:
                        action_new["extra_info"] = [
                            {
                                "instance_id": abnormal["instance_id"],
                                "ip": abnormal["ip"],
                            }
                        ]
            action_basics_add_info.append(action_new)
        return action_basics_add_info

    @staticmethod
    def get_llm_input_args(action_names, action_basics, tool_args_map):
        """
        新的匹配参数补充结果actionBasics
        """
        choose_action_basics = []
        # 得到需要执行的action
        for i in action_names:
            for j in action_basics:
                if j["tool_name_cn"] == i:
                    choose_action_basics.append(j)

        # 根据instance_id对actions进行二次拆分
        action_basics_new = []
        for action in choose_action_basics:
            extra_info = action["extra_info"]
            for id, i in enumerate(extra_info):
                if action["tool_name_cn"] == "hdfs_restart" and id > 0:
                    # hdfs_restart只要重启一次
                    continue
                ac_new = copy.deepcopy(action)
                del ac_new["extra_info"]
                ac_new.update(i)
                action_basics_new.append(ac_new)

        # 为每个action匹配tool参数描述
        actionBasics = []
        for action in action_basics_new:
            for tool in tool_args_map:
                if tool["name"] == action["tool_name_en"]:
                    new_action = copy.deepcopy(action)
                    new_action["params"] = tool["input_args_detail"]
                    actionBasics.append(new_action)
        return actionBasics

    # ============================================================
    # 步骤5：合并输出 actions 数组
    # ============================================================
    @staticmethod
    def build_actions(
        action_basics: list,
        tool_args_map: dict,
        action_names: list,
        alert_info: dict,
        abnormalInstances: list,
    ) -> list:
        """
        遍历 action_basics，为每条 action 填充 data 字段，
        合并后输出 actions 数组。
        """
        # 1.action_basics添加补充信息
        action_basics_add_info = FillParamsNode.add_extra_info(
            action_basics, abnormalInstances
        )

        # action_basics_add_info匹配对应tool_args
        actionBasics = FillParamsNode.get_llm_input_args(
            action_names, action_basics_add_info, tool_args_map
        )

        # 从配置直接获取llm配置
        actions = FillParamsNode.llm_fill_params(actionBasics, alert_info)
        return actions, action_basics_add_info

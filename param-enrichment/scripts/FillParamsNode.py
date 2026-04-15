#!/usr/bin/env python3
"""
Step 4 & 5：填充参数，合并输出
"""

import json
from scripts.config import LLM_SYSTEM_PROMPT, ENTITY_SERVICEROLE_MAP, LLM_CONFIG


class FillParamsNode:
    """
    负责填充参数并合并输出的节点
    """

    # ============================================================
    # Step 4a：规则引擎填充（LLM 降级兜底）
    # ============================================================
    @staticmethod
    def rule_based_fill(action_basic: dict, input_args: list) -> dict:
        """
        规则引擎：直接映射可确定值的参数，其余使用 default。
        """
        entity   = action_basic.get("_entity", "").lower()
        ip       = action_basic.get("extra_info", {}).get("ip", "")
        cur_val  = action_basic.get("_current_value")

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
                            num_str = ''.join(c for c in default if c.isdigit() or c == '.')
                            if num_str:
                                params[name] = float(num_str) if '.' in num_str else int(num_str)
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
    # Step 4b：LLM 智能填充
    # ============================================================
    @staticmethod
    def llm_fill_params(
        action_basic: dict,
        input_args: list,
        alert_info: dict,
        llm_config: dict,
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
        api_key = llm_config.get("api_key", LLM_CONFIG["api_key"])
        base_url = llm_config.get("base_url", LLM_CONFIG["base_url"])
        model = llm_config.get("model", LLM_CONFIG["model"])
        max_tokens = llm_config.get("max_tokens", LLM_CONFIG["max_tokens"])
        timeout = llm_config.get("timeout", LLM_CONFIG["timeout"])
        
        if not api_key:
            return FillParamsNode.rule_based_fill(action_basic, input_args)

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )

            # 构建上下文（去掉内部私有字段）
            action_for_prompt = {
                k: v for k, v in action_basic.items() if not k.startswith("_")
            }

            user_content = json.dumps({
                "alertInfo": alert_info,
                "action": action_for_prompt,
                "input_args_definition": input_args,
            }, ensure_ascii=False, indent=2)

            messages = [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )

            response_text = response.choices[0].message.content.strip()
            # 清理 Markdown 代码块
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(response_text)
            params = parsed.get("params", {})
            
            # 处理 value 参数，确保是数字类型
            if "value" in params:
                value = params["value"]
                if isinstance(value, str):
                    # 移除单位，只保留数字
                    num_str = ''.join(c for c in value if c.isdigit() or c == '.')
                    if num_str:
                        params["value"] = float(num_str) if '.' in num_str else int(num_str)
                    else:
                        # 如果无法提取数字，使用规则引擎
                        return FillParamsNode.rule_based_fill(action_basic, input_args)
            
            print(f"    ✓ LLM 填充完成，参数：{json.dumps(params, ensure_ascii=False)}")
            return params

        except Exception as e:
            print(f"    [警告] LLM 填充失败（{e}），降级到规则引擎")
            return FillParamsNode.rule_based_fill(action_basic, input_args)

    # ============================================================
    # Step 5：合并输出 actions 数组
    # ============================================================
    @staticmethod
    def build_actions(
        action_basics: list,
        tool_args_map: dict,
        alert_info: dict,
        llm_config: dict,
    ) -> list:
        """
        遍历 action_basics，为每条 action 填充 data 字段，
        合并后输出 actions 数组。
        """
        actions = []

        for ab in action_basics:
            tool_name_en = ab.get("tool_name_en", "")
            action_tag   = ab.get("action_tag", "")

            # 构建干净的输出 action（去掉内部私有字段）
            output_action = {
                k: v for k, v in ab.items() if not k.startswith("_")
            }

            if action_tag == "human":
                # 人工操作：跳过 API 查询，data 置空
                print(f"  [跳过] 人工操作：{ab.get('action_des')} ({tool_name_en})")
                output_action["data"] = {}
            else:
                input_args = tool_args_map.get(tool_name_en, [])
                print(f"  [填参] {ab.get('action_des')} ({tool_name_en})")

                if not input_args:
                    # API 未返回定义：使用规则引擎兜底
                    params = FillParamsNode.rule_based_fill(ab, [])
                    output_action["data"] = params
                else:
                    params = FillParamsNode.llm_fill_params(ab, input_args, alert_info, llm_config)
                    output_action["data"] = params

            actions.append(output_action)

        return actions
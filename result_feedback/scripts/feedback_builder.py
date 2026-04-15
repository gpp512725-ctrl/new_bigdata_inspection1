"""步骤 6-7：构造 feature_to_actions 和 check_info。"""
import copy

class FeedbackBuilder:
    """反馈构建类"""
    
    @staticmethod
    def build_feature_to_actions(action_res_all: list[dict],featureInfos,abnormal_res) -> dict[tuple[str, str], list[dict]]:
        """步骤 6：按 (feature_code, instance_id) 分组行动结果。

        从 action_res_all 中拿出所有以 (feature_code, instance_id) 为一组的唯一值，
        然后将 code、action_des、action_msg、tool_name_cn 都分别挂在这个唯一值上。
        """
        check_info = []
        for info in featureInfos:
            instance_id = info["instance_id"]
            feature_code = info["feature_code"]
            feature_to_action = []
            #先为异常特征挂上所有行动（包括人工执行）
            for action in action_res_all:
                if instance_id == action["instance_id"] and feature_code == action["feature_code"]:
                    feature_to_action.append({
                        "code": action["code"],
                        "action_des": action["action_des"],
                        "action_msg": action["action_msg"],
                        "tool_name_cn": action["tool_name_cn"]
                    })
            #查看特征是否异常，添加check_msg字段
            execute_suc = False
            for abnormal in abnormal_res:
                if instance_id == abnormal["instance_id"] and feature_code == abnormal["feature_code"]:
                    if abnormal["result"]:
                        execute_suc = True

            check_res = copy.deepcopy(info)
            check_res["feature_to_action"] = feature_to_action
            if execute_suc :
                check_msg = f"实例id为{instance_id}的故障链特征{feature_code}已修复，行动执行细节如下：" 
            else:
                check_msg = f"实例id为{instance_id}的故障链特征{feature_code}未修复，行动执行细节如下：" 
            
            check_res["check_msg"] = check_msg
            check_info.append(check_res)
        return check_info

    @staticmethod
    def build_check_info(feature_infos: list[dict],
                         feature_to_actions: dict[tuple[str, str], list[dict]],
                         check_messages: dict[tuple[str, str], str]) -> list[dict]:
        """步骤 7：整合全部特征的执行结果 check_info。

        Args:
            feature_infos: 待验证异常特征集合。
            feature_to_actions: 按特征分组的行动结果。
            check_messages: 异常验证结果文案。

        Returns:
            check_info 列表。
        """
        check_info = []

        for fi in feature_infos:
            feature_code = fi["feature_code"]
            instance_id = fi["instance_id"]
            key = (feature_code, instance_id)

            check_info.append({
                "start_time": fi["start_time"],
                "timestamp": fi["timestamp"],
                "feature_code": feature_code,
                "instance_id": instance_id,
                "feature_to_actions": feature_to_actions.get(key, []),
                "check_msg": check_messages.get(key, ""),
            })

        return check_info

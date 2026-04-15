import copy

async def main(args: Args) -> Output:
    params = args.params
    alert_bool = params['alert_bool']
    execute_conclusion = params['execute_conclusion']
    if alert_bool:
        # 检查异常结果
        alert_abnormal_res = params['alert_abnormal_res']
        alert_feature = params['alert_feature'][0]
        unique_feature = params['unique_feature']
        execute_suc = False
        for info in alert_abnormal_res:
            instance_id = info['instance_id']
            feature_code = info['feature_code']
            # 检查特征
            if instance_id == alert_feature['instance_id'] and feature_code == alert_feature['feature_code']:
                if info['result']:
                    execute_suc = True

        unique_feature_str = ",".join(unique_feature)
        alert_msg = ""
        if execute_suc:
            alert_msg = f"检测到示例id{alert_feature['instance_id']}的{alert_feature['feature_code']}特征已恢复正常，故障已修复。故障链特征包括{unique_feature_str}。\n修复过长说明：\n"
        else:
            alert_msg = f"检测到示例id{alert_feature['instance_id']}的{alert_feature['feature_code']}特征尚未恢复正常，故障链特征包括{unique_feature_str}。\n修复过长说明：\n"
        conclusion = "\n\n".join([i["conclusion"] for i in execute_conclusion ])
        execute_conclusion = [{"feature_code": alert_feature['feature_code'],
                               "instance_id": alert_feature['instance_id'],
                               "conclusion": alert_msg + conclusion}]
    else:
        execute_conclusion= execute_conclusion
    ret: Output = {
        "execute_conclusion": execute_conclusion,
    }
    return ret

import os
from datetime import timezone, timedelta

# 项目路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
REFERENCE_DIR = os.path.join(PROJECT_ROOT, "reference")

# 时间配置
CST = timezone(timedelta(hours=8))
VERIFY_WINDOW_SECONDS = 120

# 异常判断 API 配置
ABNORMAL_DETECTION_API = {
            "url": "https://192.168.10.54/api/feature/feature_actions/judge_exception",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                # "Authorization": "Bearer YOUR_API_TOKEN"
            },
            "timeout": 300,
            "enabled": False  # 默认禁用，使用mock数据
        }

# LLM 配置
LLM_CONFIG = {
            "api_key": "sk-18d889d62ad74d60875b2fd8dd88f254",  # 大模型API密钥
            "model": "qwen3.5-plus",  # 模型名称
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # API基础URL
            "temperature": 0.3,  # 温度参数
            "max_tokens": 2000  # 最大 token 数
        }

# 数据库配置（预留）
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "result_feedback",
    "charset": "utf8mb4",
}

ALARM_PROB_LIMIT =0.85
KEEP_DETAIL_RATIO =0.3

LLM_PROMPT="""
#角色
你是一个大数据运维场景的专业客服，能够将故障修复情况进行总结整理，转换成专业话术，呈现给客户。

##技能
### 技能1：理解行动执行结果的含义
1. feature_code是检测特征; instance_id是实例id; check_msg是当前检测特征; 对应实例id的诊断结果;
2. feature_to_action表示为了修复特征, 采取的行动信息, 包括:
- tool_name_cn: 行动的名称;
- action_msg: 表示采取行动的具体说明;

### 技能2: 输出修复结论
修复结论输出内容格式如下:

* 首先通过当前检测特征, 对应实例id的诊断结果, 即check_msg;
* 其次展开"feature_to_action", 介绍每个具体的行动名称和执行结果, 其中, 采取的具体行动标志="tool_name_cn", 执行结果="action_msg"; 格式:
1) 采取的tool_name_cn行动的执行结果action_msg
2) 采取的tool_name_cn行动的执行结果action_msg

### 特别注意:
* 如果行动结果为空, 表示不显示;
* 如果行动结果有值, 则显示;
* 输出修复结论时, 结果必须是"action_msg"字段, 请不要输出"action_des"字段。

-示例json结果: [{conclusion: 实例id=yes-bigdata-self-hadoop-2:27001的诊断特征在Hadoop_NameNode_NonDfsUsedSpace已经修复。行动内容如下: "检测到磁盘空间占用率高, 已经清理日志及临时文件, 并重启相关服务;", instance_id:"yes-bigdata-self-hadoop-2:27001", feature_code:"Hadoop_NameNode_NonDfsUsedSpace"}]。

##限制
1.仅围绕故障修复结果进行输出。
2.输出内容与格式，严格按照要求来。
3.语言尽可能简洁，不要过于啰嗦

"""
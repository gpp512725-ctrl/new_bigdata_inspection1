---
name: param-enrichment
description: 大数据集群巡检参数补充技能——根据用户指定的action_name，通过API接口动态获取MCP工具入参定义，结合故障告警信息与巡检分析报告，由LLM智能填充参数值，输出可执行的actions JSON。当用户需要"参数补充"、"补充MCP入参"、"行动参数填充"或"actions输出"时，必须使用本技能。
---

# 参数补充技能

## 概述

本技能通过外部 API 动态拉取 MCP 工具的入参定义，结合 [巡检分析报告] 中的 `action_basics` 和 `abnormalInstances`，以及当前告警信息 `alertInfo`，根据用户指定的 `action_name` 匹配对应工具，由 LLM 理解参数含义后智能填充参数值，最终输出完整的 `actions` 数组。

---

## 工作流步骤

```
1. 读取 action_basics
   └─ 提取 action_des / action_tag / extra_info / feature_code
      / tool_name_cn / tool_name_en / action_priority

2. 过滤非人工操作 action
   └─ action_tag != "human" → 提取 tool_name_cn 列表（用于匹配 action_names）

3. 匹配用户指定的 action_names
   └─ action_names 与 action_basics 的 tool_name_cn 进行匹配

4. 调用工具入参 API
   └─ GET /api/mcp/tool/args?tool_name={tool_name_en}
   └─ 解析 input_args：name / type / default / description

5. LLM 智能填充参数值
   └─ 输入：alertInfo + action_basics + input_args 定义
   └─ 输出：每个工具的 {param_name: param_value} dict

6. 合并输出 actions
   └─ data(入参dict) + action_basics 原字段 → actions 数组
```

---

## API 配置

> ⚠️ 以下配置项必须在调用前确认，可通过环境变量或配置文件传入。

### 工具入参查询 API

```python
API_CONFIG = {
    "base_url":  "http://<YOUR_HOST>:<PORT>",   # 工具入参查询服务地址
    "username":  "<USERNAME>",                   # Basic Auth 用户名
    "password":  "<PASSWORD>",                   # Basic Auth 密码
    "app_id":    "<APP_ID>",                     # 应用标识，放入 Header: X-App-Id
    "timeout":   10,                             # 请求超时秒数
}
```

### LLM 配置（参数智能填充）

```python
LLM_CONFIG = {
    "api_key":   "<ANTHROPIC_API_KEY>",          # Anthropic API Key，也可通过环境变量 ANTHROPIC_API_KEY 传入
    "base_url":  "https://api.anthropic.com",    # API 地址，私有化部署时修改此项
    "model":     "claude-sonnet-4-20250514",     # 使用的模型，可替换为其他版本
    "max_tokens": 512,                           # 单次填参最大输出 token 数
    "timeout":   30,                             # LLM 请求超时秒数
}
```

> 说明：未配置 `api_key` 时，自动降级为规则引擎填充（仅根据 `extra_info.ip`、实体类型等直接映射，不调用 LLM）。

**接口说明**

| 字段 | 说明 |
|------|------|
| Method | GET |
| Path | `/api/mcp/tool/args` |
| Query Param | `tool_name`（工具英文名，即 `tool_name_en`） |
| Auth | HTTP Basic Auth（username / password） |
| Header | `X-App-Id: <app_id>` |

**响应结构**

```json
{
  "code": 0,
  "data": {
    "tool_name": "hdfs_restart",
    "input_args": [
      {
        "name": "ip",
        "type": "string",
        "default": "",
        "description": "目标节点IP地址"
      },
      {
        "name": "servicerole",
        "type": "string",
        "default": "NAMENODE",
        "description": "服务角色，枚举：NAMENODE / DATANODE"
      },
      {
        "name": "commandtype",
        "type": "string",
        "default": "restart",
        "description": "命令类型，枚举：restart / start / stop"
      }
    ]
  }
}
```

---

## action_basics 字段说明

从 Agent 2（巡检分析报告）输出中获取，每条 action 包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `action_des` | string | 行动描述，如"扩容NN堆内存" |
| `action_tag` | string | `"human"`=手动操作 / `""`(空字符串)=自动执行 |
| `extra_info` | object | 执行对象信息，含 `instance_id`、`ip` |
| `feature_code` | string | 执行后可修复的特征编码 |
| `tool_name_cn` | string | MCP工具中文名称 |
| `tool_name_en` | string | MCP工具英文名称（同时也是工具调用名） |
| `action_priority` | int | 优先级，数字越小越优先 |

---

## LLM 参数填充规则

LLM 接收以下上下文进行参数推断：

1. **alertInfo**：当前告警信息（含异常特征、当前值、阈值、实例IP等）
2. **action_basics 单条**：当前行动的完整描述（含 `extra_info` 中的实例IP）
3. **input_args 定义列表**：每个参数的 name/type/default/description

**填充优先级**：
- 能从 `extra_info.ip` 直接取值的参数（如 `ip`）→ 直接填入
- 有明确枚举值的参数 → 根据实体类型（namenode/datanode）映射
- 有默认值且无更好参考的参数 → 使用 default
- 需要根据当前指标计算的参数（如扩容值）→ LLM 结合 alertInfo 推算建议值

---

## 输出格式：actions 数组

```json
[
  {
    "action_des": "扩容NN堆内存",
    "action_tag": "",
    "extra_info": {
      "instance_id": "nn-host-01",
      "ip": "192.168.1.10"
    },
    "feature_code": "NameNode_Heap_Memory_Usage_Rate",
    "tool_name_cn": "扩容NN堆内存",
    "tool_name_en": "namenode_heap_memory_expand",
    "action_priority": 1,
    "data": {
      "value": "8g"
    }
  },
  {
    "action_des": "重启HDFS服务",
    "action_tag": "",
    "extra_info": {
      "instance_id": "nn-host-01",
      "ip": "192.168.1.10"
    },
    "feature_code": "NameNode_Heap_Memory_Usage_Rate",
    "tool_name_cn": "重启HDFS服务",
    "tool_name_en": "hdfs_restart",
    "action_priority": 2,
    "data": {
      "ip": "192.168.1.10",
      "servicerole": "NAMENODE",
      "commandtype": "restart"
    }
  }
]
```

**关键规则**：
- `data` 字段与 `action_des`、`action_tag` 等字段**同级**
- `action_tag == "human"` 的行动：**跳过 API 查询**，`data` 置为空对象 `{}`
- 最终输出为纯 JSON 数组，命名为 `actions`

---

## 脚本入口

```bash
python main.py -i input.json -o output.json
```

详见 `main.py` (位于技能根目录)

---

## 输入字段

| 字段名 | 类型 | 说明 | 数据源 |
|-------|------|------|--------|
| `action_names` | array | 用户指定要执行的行动名称数组，用于匹配 actionBasics 中的 tool_name_cn | 外部用户交互输入 |
| `actionBasics` | array | 行动基础信息列表，包含行动描述、工具名称等 | 【巡检分析报告Skill】的输出 |
| `abnormalInstances` | array | 异常实例列表，包含实例IP、实体名称等 | 【排查异常实体Skill】的输出 |
| `alertInfo` | object | 告警信息，包含主机、值、严重程度等 | 整个Agent最初始的输入 |
| `api_config` | object | API 配置信息（可选，也可通过环境变量或命令行参数传入） | 环境配置 |
| `llm_config` | object | LLM 配置信息（可选，也可通过环境变量或命令行参数传入） | 环境配置 |

### 输入格式示例

#### alertInfo
```json
{
  "host": "192.168.10.178",
  "unit": "",
  "value": 0,
  "duration": 15,
  "severity": "Exception",
  "timestamp": "2025-10-30 15:12:51",
  "feature_id": 6808,
  "topic_name": "Hadoop",
  "entity_name": "Namenode",
  "instance_id": "Yes-Bigdata-Self-Hadoop-2:27001",
  "feature_code": "Up_Namenode",
  "feature_name": "Namenode进程存活",
  "instance_name": "Yes-Bigdata-Self-Hadoop-2:27001",
  "parent_entity_name": "Hdfs"
}
```

#### action_names
```json
[
  "重启HDFS服务",
  "扩容NN堆内存"
]
```

#### actionBasics
```json
[
  {
    "action_des": "增加-Xmx值，适用于内存不足场景",
    "action_tag": "",
    "feature_code": "NameNode_Heap_Memory_Usage_Rate",
    "tool_name_cn": "扩容NN堆内存",
    "tool_name_en": "namenode_heap_memory_expand",
    "action_priority": "高"
  },
  {
    "action_des": "重启namenode，适用于进程异常退出、修改参数后重启以生效等场景",
    "action_tag": "human",
    "feature_code": "NameNode_Heap_Memory_Usage_Rate",
    "tool_name_cn": "重启HDFS服务",
    "tool_name_en": "hdfs restart",
    "action_priority": "低"
  }
]
```

#### abnormalInstances
```json
[
  {
    "ip": "192.168.10.178",
    "entity_name": "node",
    "instance_id": "yes-bigdata-self-hadoop-2:9100",
    "feature_code": "Host_Memory_Usage_Rate"
  },
  {
    "ip": "192.168.10.177",
    "entity_name": "namenode",
    "instance_id": "yes-bigdata-self-hadoop-1:27001",
    "feature_code": "Hadoop_NameNode_NonDfsUsedSpace"
  },
  {
    "ip": "192.168.10.178",
    "entity_name": "namenode",
    "instance_id": "yes-bigdata-self-hadoop-2:27001",
    "feature_code": "Hadoop_NameNode_NonDfsUsedSpace"
  },
  {
    "ip": "192.168.10.177",
    "entity_name": "namenode",
    "instance_id": "yes-bigdata-self-hadoop-1:27001",
    "feature_code": "NameNode_Heap_Memory_Usage_Rate"
  },
  {
    "ip": "192.168.10.178",
    "entity_name": "namenode",
    "instance_id": "yes-bigdata-self-hadoop-2:27001",
    "feature_code": "NameNode_Heap_Memory_Usage_Rate"
  },
  {
    "ip": "192.168.10.177",
    "entity_name": "namenode",
    "instance_id": "yes-bigdata-self-hadoop-1:27001",
    "feature_code": "Hadoop_NameNode_GcTimeMillis"
  }
]
```

## 输出结构

```json
[
  {
    "action_des": "扩容NN堆内存",
    "action_tag": "",
    "extra_info": {
      "instance_id": "nn-host-01",
      "ip": "192.168.1.10"
    },
    "feature_code": "NameNode_Heap_Memory_Usage_Rate",
    "tool_name_cn": "扩容NN堆内存",
    "tool_name_en": "namenode_heap_memory_expand",
    "action_priority": 1,
    "data": {
      "value": "8g"
    }
  }
]
```

## 错误处理

| 情况 | 处理方式 |
|------|---------|
| API 请求失败 | 打印警告，`data` 填入空对象，继续处理 |
| 工具不存在（404） | 同上 |
| LLM 调用失败 | 降级为规则引擎填充（仅填 `ip`、`servicerole`、`commandtype` 等可直接映射字段）
| `action_tag == "human"` | 跳过 API 查询，`data = {}`
| 未找到匹配的 action_name | 输出空数组 |
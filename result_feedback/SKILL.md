---
name: result_feedback
description: 结果反馈技能 - 根据行动执行结果生成自然语言的修复结论，向用户反馈各项行动的执行状态和最终效果
---

# Result Feedback Skill - 结果反馈技能

## 概述
本技能负责根据行动执行结果生成自然语言的修复结论，向用户反馈各项行动的执行状态和最终效果，支持批量行动结果的汇总输出。

## 触发条件
当用户需要生成修复结论、查看行动执行反馈、或需要将结构化执行结果转换为自然语言报告时触发本技能。

## 核心流程
```
输入 (action_res + action_basics) → LLM 分析 → 生成修复结论 → 输出 (execute_conclusion)
```

## 执行方式

### 命令行执行
```bash
python main.py -i input.json -o output.json
```

### 命令行参数
| 参数 | 简写 | 说明 | 默认值 |
|---|---|---|---|
| `--input-file` | `-i` | 输入 JSON 文件路径 | `input.json` |
| `--output-file` | `-o` | 输出 JSON 文件路径 | `output.json` |

### Python 代码调用
```python
from result_analyzer import ResultAnalyzer

analyzer = ResultAnalyzer()
conclusion = analyzer.generate_conclusion(
    action_res=[...],
    action_basics=[...]
)
```

## 输入字段

### 顶层字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| action_res | list[object] | 是 | 行动执行结果列表（来自 action_execution 技能输出） |
| action_basics | list[object] | 否 | 行动基础信息列表（可选，用于增强结论描述） |

### action_res 列表中每个对象的字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| tool_name_cn | string | 工具中文名称 |
| instance_id | string | 实例对象 ID |
| feature_code | string | 特征对象编码 |
| execute_time | string | 执行时间 |
| action_des | string | 行动描述 |
| code | number | 执行结果代码（1=成功，0=失败） |
| action_msg | string | 执行信息文案 |

### 输入示例
```json
{
  "action_res": [
    {
      "tool_name_cn": "调整阈值",
      "instance_id": "INST_001",
      "feature_code": "FEAT_001",
      "execute_time": "2026-04-01 10:30:00",
      "action_des": "将设备 A 的温度阈值调整为 85 度",
      "code": 1,
      "action_msg": "调整阈值为 MCP 执行，且执行成功"
    },
    {
      "tool_name_cn": "重启服务",
      "instance_id": "INST_002",
      "feature_code": "FEAT_002",
      "execute_time": "2026-04-01 10:31:00",
      "action_des": "重启设备 B 的服务",
      "code": 1,
      "action_msg": "重启服务为 MCP 执行，且执行成功"
    }
  ],
  "action_basics": [
    {
      "action_name": "调整阈值",
      "action_type": "config_change",
      "target_component": "TemperatureSensor"
    }
  ]
}
```

## 输出结构

### 顶层字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| execute_conclusion | list[object] | 修复结论列表，每个行动一条结论 |

### execute_conclusion 列表中每个对象的字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| tool_name_cn | string | 工具中文名称 |
| instance_id | string | 实例对象 ID |
| feature_code | string | 特征对象编码 |
| conclusion | string | 自然语言修复结论 |

### 输出示例
```json
{
  "execute_conclusion": [
    {
      "tool_name_cn": "调整阈值",
      "instance_id": "INST_001",
      "feature_code": "FEAT_001",
      "conclusion": "调整阈值行动已成功执行，设备 A 的温度阈值已调整为 85 度，当前运行正常。"
    },
    {
      "tool_name_cn": "重启服务",
      "instance_id": "INST_002",
      "feature_code": "FEAT_002",
      "conclusion": "重启服务行动已成功执行，设备 B 的服务已重启完成，当前运行正常。"
    }
  ]
}
```

## 依赖配置
- **LLM 服务**: 需要配置可用的 LLM 模型用于生成自然语言结论
- **Python 环境**: 需要安装相关依赖

## 文件结构
```
result_feedback/
├── SKILL.md              # 技能说明文件
├── main.py               # 主入口脚本
├── result_analyzer.py    # 结果分析核心逻辑
├── llm_client.py         # LLM 调用客户端
├── config.py             # 配置文件
├── input.json            # 输入文件（运行时生成）
└── output.json           # 输出文件（运行时生成）
```

## 错误处理
| 情况 | 处理方式 |
|---|---|
| action_res 为空 | 输出空结论列表 |
| LLM 调用失败 | 使用模板生成基础结论 |
| 输入格式错误 | 报错并终止 |
| 部分行动失败 | 在结论中标注失败状态 |

## 注意事项
1. 支持批量生成多条行动的修复结论
2. 结论语言风格应保持专业、简洁、易懂
3. 失败行动需在结论中明确标注失败原因
4. 可结合 action_basics 增强结论的详细程度

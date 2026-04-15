---
name: action-execution-analyst
description: 行动执行分析员技能 - 串联 param-enrichment、action_execution 和 result_feedback 三个技能，实现从原始行动信息输入到最终修复结论输出的完整闭环
---

# Action Execution Analyst Skill - 行动执行分析员技能

## 概述
本技能是一个串联型自动化技能，负责将行动执行的全流程自动化。它依次调用 `param-enrichment`、`action_execution` 和 `result_feedback` 三个技能，实现从原始行动信息输入到最终修复结论输出的完整闭环。

## 触发条件
当用户需要执行完整的行动执行分析流程、或调用行动执行分析员技能时触发本技能。

## 核心流程
```
input_path or input (原始行动信息)
    │
    ▼
┌─────────────────────────────────┐
│ 1. param-enrichment             │
│    输入：input_path  or input           │
│    输出：output_path (actions)  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. action_execution             │
│    输入：上一步的 output_path   │
│    输出：output (action_res)    │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. result_feedback              │
│    输入：上一步的 output        │
│    输出：output (execute_conclusion) │
└─────────────────────────────────┘
    │
    ▼
最终输出：execute_conclusion
```

## 执行方式

### 命令行执行
```bash
# 使用自定义输入文件
python main.py -i "C:\path\to\input.json" -o "C:\path\to\output.json"

# 使用 JSON 字符串输入
python main.py --input "{\"alertInfo\":{}}", -o "C:\path\to\output.json"
```

### 命令行参数
| 参数 | 简写 | 说明 | 默认值 |
|---|---|---|---|
| `--input-file` | `-i` | 输入 JSON 文件真实路径 | `input.json` |
| `--input` | null | 输入 JSON 字符串 | null |
| `--output-file` | `-o` | 输出 JSON 文件路径 | `output.json` |



## 输入字段
### input-file 文件包含内容或input json包含内容
| 字段名 | 类型 | 说明 |
|---|---|---|
| action_names | list[string] | 行动名称列表 |
| actionBasics | list[object] | 行动基础信息 |
| abnormalInstances | list[object] | 异常实例信息 |
| alertInfo | object | 告警信息（可选） |

### 输入示例内容：
```json
{
  "action_names": ["重启 HDFS 服务", "扩容 NN 堆内存"],
  "actionBasics": [...],
  "abnormalInstances": [...],
  "alertInfo": null
}
```

## 输出结构

### 顶层字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| execute_conclusion | string | LLM 生成的自然语言修复结论 |
| success | boolean | 流程是否成功完成 |
| error | string | 错误信息（失败时） |
| intermediate_outputs | object | 中间输出文件路径（用于调试） |

### intermediate_outputs 字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| param_enrichment_output | string | param-enrichment 的输出文件路径 |
| action_execution_output | string | action_execution 的输出文件路径 |
| result_feedback_output | string | result_feedback 的输出文件路径 |

### 输出示例
```json
{
  "execute_conclusion": "经过执行修复行动，所有异常特征均已恢复正常。扩容 NN 堆内存行动已成功执行，重启 HDFS 服务行动已成功执行，当前系统运行正常。",
  "success": true,
  "error": null,
  "intermediate_outputs": {
    "param_enrichment_output": "C:\\path\\to\\temp\\param_enrichment_xxx.json",
    "action_execution_output": "C:\\path\\to\\temp\\action_execution_xxx.json",
    "result_feedback_output": "C:\\path\\to\\temp\\result_feedback_xxx.json"
  }
}
```

## 工作流程详解

### 步骤 1: 调用 param-enrichment
- 读取 input_path or input 中的原始行动信息
- 调用 param-enrichment 技能进行参数补充
- 输出包含完整 actions 数组的 JSON 文件

### 步骤 2: 调用 action_execution
- 使用上一步输出的 actions 作为输入
- 调用 action_execution 技能执行各项行动
- 输出包含 action_res 执行结果列表的 JSON 文件

### 步骤 3: 调用 result_feedback
- 使用上一步输出的 action_res 作为输入
- 调用 result_feedback 技能生成修复结论
- 输出包含 execute_conclusion 的最终结果

## 依赖配置
| 依赖项 | 路径 | 说明 |
|---|---|---|
| param-enrichment | `.\skills\param-enrichment` | 参数补充技能 |
| action_execution | `.\skills\action_execution` | 行动执行技能 |
| result_feedback | `.\skills\result_feedback` | 结果反馈技能 |
| Python 环境 | - | 需要安装相关依赖 |

## 文件结构
```
action-execution-analyst/
├── SKILL.md              # 技能说明文件
├── README.md             # 使用指南
├── main.py               # 主入口脚本
├── scripts/
│   └── orchestrator.py   # 流程编排器
├── temp/                 # 临时文件目录（运行时生成）
├── test_data/
│   └── action_info.json  # 测试数据
└── input.json    # 示例输入
```

## 错误处理
| 情况 | 处理方式 |
|---|---|
| param-enrichment 失败 | 终止流程，输出错误信息 |
| action_execution 失败 | 继续执行 result_feedback，但标记执行状态 |
| result_feedback 失败 | 输出已执行的行动结果，结论标记为部分完成 |
| 输入文件不存在 | 报错并终止 |

## 注意事项
1. 执行前确保三个依赖技能均可正常调用
2. 临时文件目录 `temp/` 会在执行时自动创建
3. 执行完成后可选择保留或清理临时文件
4. 中间输出文件路径可在最终输出的 `intermediate_outputs` 中查看

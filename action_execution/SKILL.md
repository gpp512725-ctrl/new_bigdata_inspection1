---
name: action_execution
description: 行动执行技能 - 负责执行具体的修复行动，调用 MCP 工具完成参数调整、服务重启、配置变更等操作
---

# Action Execution Skill - 行动执行技能

## 概述
本技能负责执行具体的修复行动，调用相应的 MCP 工具完成参数调整、服务重启、配置变更等操作，并输出结构化的执行结果。

## 触发条件
当用户需要执行修复行动、调用行动执行技能、或需要批量执行多个 MCP 工具时触发本技能。

## 核心流程
```
输入 (actions) → 解析行动参数 → 调用 MCP 工具 → 收集执行结果 → 输出 (action_res)
```

## 执行方式

### 命令行执行
```bash
cd C:\Users\wulang\.openclaw\workspace\skills\action_execution
python main.py -i input.json -o output.json
```

### 命令行参数
| 参数 | 简写 | 说明 | 默认值 |
|---|---|---|---|
| `--input-file` | `-i` | 输入 JSON 文件路径 | `input.json` |
| `--output-file` | `-o` | 输出 JSON 文件路径 | `output.json` |

### Python 代码调用
```python
from action_executor import ActionExecutor

executor = ActionExecutor()
result = executor.execute_actions(actions=[...])
```

## 输入字段

### 顶层字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| actions | list[object] | 是 | 待执行的行动列表，每个行动包含 tool_name 和 tool_args |

### actions 列表中每个对象的字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| tool_name | string | MCP 工具名称（英文标识符） |
| tool_name_cn | string | MCP 工具中文名称 |
| tool_args | object | 工具调用参数（键值对） |
| instance_id | string | 目标实例 ID |
| feature_code | string | 关联的特征编码 |
| action_des | string | 行动描述 |

### 输入示例
```json
{
  "actions": [
    {
      "tool_name": "adjust_threshold",
      "tool_name_cn": "调整阈值",
      "tool_args": {
        "instance_id": "INST_001",
        "threshold_value": 85
      },
      "instance_id": "INST_001",
      "feature_code": "FEAT_001",
      "action_des": "将设备 A 的温度阈值调整为 85 度"
    }
  ]
}
```

## 输出结构

### 顶层字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| action_res | list[object] | 行动执行结果列表 |

### action_res 列表中每个对象的字段
| 字段名 | 类型 | 说明 |
|---|---|---|
| tool_name_cn | string | 工具中文名称 |
| instance_id | string | 实例对象 ID |
| feature_code | string | 特征对象编码 |
| execute_time | string | 执行时间（YYYY-MM-DD HH:MM:SS） |
| action_des | string | 行动描述 |
| code | number | 执行结果代码（1=成功，0=失败） |
| action_msg | string | 执行信息文案 |

### 输出示例
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
    }
  ]
}
```

## 依赖配置
- **MCP 工具集**: 需要配置可用的 MCP 工具（如 adjust_threshold, restart_service 等）
- **Python 环境**: 需要安装相关依赖

## 文件结构
```
action_execution/
├── SKILL.md              # 技能说明文件
├── main.py               # 主入口脚本
├── action_executor.py    # 行动执行核心逻辑
├── mcp_client.py         # MCP 工具调用客户端
├── config.py             # 配置文件
├── input.json            # 输入文件（运行时生成）
└── output.json           # 输出文件（运行时生成）
```

## 错误处理
| 情况 | 处理方式 |
|---|---|
| MCP 工具不存在 | 记录错误，继续执行下一个行动 |
| 工具调用失败 | 记录失败原因，code=0 |
| 参数格式错误 | 跳过该行动，记录日志 |
| 输入文件无效 | 报错并终止 |

## 注意事项
1. 执行前确保 MCP 工具已正确配置并可调用
2. 支持批量执行多个行动，按顺序依次执行
3. 单个行动失败不影响其他行动的执行
4. 执行结果包含详细的执行时间和状态信息

# 行动执行分析员 (Action Execution Analyst)

## 快速开始

### 1. 准备输入文件

创建输入 JSON 文件，指定原始行动信息路径：

```json
{
  "input_path": "path/to/your/action_info.json"
}
```

### 2. 执行技能

```bash
cd C:\Users\wulang\.openclaw\workspace\skills\action-execution-analyst
python main.py -i example_input.json -o output.json
```

### 3. 查看结果

输出文件包含：
- `execute_conclusion`: 最终修复结论
- `intermediate_outputs`: 中间输出文件路径（用于调试）

## 文件结构

```
action-execution-analyst/
├── SKILL.md              # 技能说明
├── README.md             # 使用指南
├── main.py               # 主入口
├── scripts/
│   └── orchestrator.py   # 流程编排器
├── temp/                 # 临时文件目录（运行时生成）
├── test_data/
│   └── action_info.json  # 测试数据
└── example_input.json    # 示例输入
```

## 依赖技能

确保以下技能已正确配置并可执行：
- `param-enrichment`: 参数补充
- `action_execution`: 行动执行
- `result_feedback`: 结果反馈

# s03 - 会话规划与 Todo 管理 (Session Planning)

## 概述

`s03_todo_write.py` 演示了轻量级会话规划机制。模型可以在对话中维护任务计划，保持一个活跃步骤在执行中，并在长时间不更新时收到提醒。

## 核心概念

| 概念 | 说明 |
|------|------|
| PlanItem | 单个计划项：content、status、activeForm |
| PlanningState | 规划状态：items 列表、rounds_since_update |
| TodoManager | 规划管理器：更新、提醒、渲染 |

## 计划项状态

| 状态 | 标记 | 说明 |
|------|------|------|
| pending | `[ ]` | 待处理 |
| in_progress | `[>]` | 执行中 |
| completed | `[x]` | 已完成 |

## 关键规则

1. **最多 12 项**: 保持计划简短
2. **同时只能有 1 个 in_progress**: 避免分散注意力
3. **3 轮无更新触发提醒**: 防止遗忘更新计划

## TodoManager 核心方法

| 方法 | 功能 |
|------|------|
| `update(items)` | 更新计划项 |
| `note_round_without_update()` | 记录无更新轮次 |
| `reminder()` | 生成提醒（超阈值时） |
| `render()` | 渲染计划文本 |

## 提醒机制

```python
PLAN_REMINDER_INTERVAL = 3

def reminder(self) -> str | None:
    if self.state.rounds_since_update < PLAN_REMINDER_INTERVAL:
        return None
    return "<reminder>Refresh your current plan before continuing.</reminder>"
```

## 工具接口

| 工具 | 参数 | 说明 |
|------|------|------|
| `todo` | items | 重写当前会话计划 |

### todo 工具 schema

```json
{
  "items": [
    {
      "content": "任务描述",
      "status": "pending | in_progress | completed",
      "activeForm": "当前进行的动作（可选）"
    }
  ]
}
```

## 状态流转

```
模型调用 todo -> update() -> rounds_since_update = 0
模型未调用 todo -> note_round_without_update() -> rounds++
模型调用 todo -> reminder() = None（未触发）
连续3轮无调用 -> reminder() = "<reminder>..."
```

## 与 s12 任务系统的区别

| 特性 | s03 Todo | s12 TaskSystem |
|------|----------|----------------|
| 生命周期 | 单会话 | 跨会话持久 |
| 存储位置 | 内存 | 磁盘 (.tasks/) |
| 依赖管理 | 无 | blockedBy 依赖图 |
| 规模 | 轻量（≤12项） | 重量级工作项 |

## 测试方法

```bash
python s03_todo_write.py
```

### 交互示例

```
s03 >> 创建一个计划：1) 读取 README.md，2) 创建 test.py，3) 运行测试

[TODO] Plan updated:
[>] 读取 README.md
[ ] 创建 test.py
[ ] 运行测试

(0/3 completed)

s03 >> 完成第一步

[TODO] Plan updated:
[x] 读取 README.md
[>] 创建 test.py
[ ] 运行测试

(1/3 completed)
```

### 测试提醒机制

1. 连续 3 次不调用 todo 工具
2. 第 4 次会收到提醒

## 输出格式

```
[>] 正在读取文件 (opening file.txt)
[x] 已完成的任务
[ ] 待处理的任务

(1/3 completed)
```

## 目录结构

```
learn_claude_code/
├── s03_todo_write.py
└── s03_README.md
```

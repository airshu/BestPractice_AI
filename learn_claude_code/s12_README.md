# s12 - 任务系统 (Task System)

## 概述

`s12_task_system.py` 演示了一个持久化任务管理系统。任务以 JSON 文件形式存储在 `.tasks/` 目录中，跨越对话持久化，不受上下文压缩影响。

## 核心概念

```
.tasks/
  task_1.json  {"id":1, "subject":"...", "status":"completed", ...}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending", ...}
  task_3.json  {"id":3, "blockedBy":[2], "blocks":[], ...}
```

**关键思想**: 任务状态存在于磁盘上，而非对话内存中，因此能经受上下文压缩存活。

## TaskRecord 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 唯一标识，自动递增 |
| `subject` | str | 任务标题 |
| `description` | str | 任务描述 |
| `status` | str | pending / in_progress / completed / deleted |
| `blockedBy` | list | 依赖的前置任务 ID 列表 |
| `blocks` | list | 阻塞的后续任务 ID 列表 |
| `owner` | str | 任务负责人 |

## TaskManager 类

### 核心方法

| 方法 | 功能 |
|------|------|
| `create(subject, description)` | 创建新任务 |
| `get(task_id)` | 获取任务详情 |
| `update(task_id, ...)` | 更新任务状态/负责人/依赖 |
| `list_all()` | 列出所有任务 |
| `clear_all()` | 清空所有任务 |

### 依赖管理

```python
# 创建任务
TASKS.create("实现登录功能", "需要支持 OAuth")

# 设置依赖：任务2 依赖 任务1
TASKS.update(2, add_blocked_by=[1])

# 双向维护：同时更新 task_2 的 blockedBy
# 和 task_1 的 blocks
```

### 依赖图解析

```
+----------+     +----------+     +----------+
| task 1   | --> | task 2   | --> | task 3   |
| complete |     | blocked  |     | blocked  |
+----------+     +----------+     +----------+
     |
     +--- 完成任务 1 后，自动从 task 2 的 blockedBy 移除
```

**自动依赖解除**: 当任务标记为 `completed` 时，自动从其他任务的 `blockedBy` 中移除。

## 任务工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `task_create` | subject, description | 创建任务 |
| `task_update` | task_id, status, owner, addBlockedBy, addBlocks | 更新任务 |
| `task_list` | - | 列出所有任务 |
| `task_get` | task_id | 获取任务详情 |
| `task_clear` | - | 清空所有任务 |

## 状态标记

| 状态 | 标记 | 说明 |
|------|------|------|
| pending | `[ ]` | 待处理 |
| in_progress | `[>]` | 进行中 |
| completed | `[x]` | 已完成 |
| deleted | `[-]` | 已删除 |

## 使用示例

```bash
python s12_task_system.py
```

### 交互示例

```
s12 >> 创建一个任务：实现用户登录功能

s12 >> 再创建两个任务：1) 数据库设计 2) API开发

s12 >> 列出所有任务
[ ] #1: 实现用户登录功能
[ ] #2: 数据库设计
[ ] #3: API开发

s12 >> 把任务2设置为依赖任务1

s12 >> 列出所有任务
[ ] #1: 实现用户登录功能
[ ] #2: 数据库设计 (blocked by: [1])
[ ] #3: API开发 (blocked by: [2])

s12 >> 把任务1改为已完成

s12 >> 列出所有任务
[x] #1: 实现用户登录功能
[ ] #2: 数据库设计  (blocked by 已自动清除)
[ ] #3: API开发 (blocked by: [2])

s12 >> 清空所有任务
Cleared 3 task(s).

s12 >> q
```

## 与其他模块对比

| 模块 | 数据位置 | 用途 |
|------|---------|------|
| s06 上下文压缩 | 内存 | 减少 token 消耗 |
| s09 记忆系统 | 内存/磁盘 | 长期知识存储 |
| s11 错误恢复 | 内存 | 容错和重试 |
| **s12 任务系统** | **磁盘** | **持久化工作项** |

## 目录结构

```
learn_claude_code/
├── .tasks/              # 任务存储目录
│   ├── task_1.json
│   ├── task_2.json
│   └── ...
├── s12_task_system.py   # 主脚本
└── s12_README.md        # 本文档
```

## 注意事项

1. **ID 持久性**: 任务 ID 连续递增，清空后重置为 1
2. **双向依赖**: 添加 `blocks` 时自动维护 `blockedBy` 关系
3. **文件安全**: 使用 `safe_path()` 防止路径穿越攻击

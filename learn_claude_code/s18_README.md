# s18 - Worktree + Task Isolation

目录级隔离的并行任务执行。任务作为控制平面，worktree 作为执行平面。

## 核心概念

**关键洞察**: "通过目录隔离，通过任务 ID 协调"

```
任务 (控制平面)          Worktree (执行平面)
+-------------+          +------------------+
| task_12.json| <------> | .worktrees/     |
| worktree:   |          |   auth-refactor/ |
| "auth-refactor"        +------------------+
+-------------+
```

## 三大组件

| 组件 | 功能 | 存储 |
|------|------|------|
| `EventBus` | 生命周期事件可观测 | `.worktrees/events.jsonl` |
| `TaskManager` | 任务 + worktree 绑定 | `.tasks/task_*.json` |
| `WorktreeManager` | Git worktree 生命周期 | `.worktrees/index.json` |

## 生命周期

```
worktree_create ──> worktree_run ──> worktree_closeout (keep/remove)
       │                               │
       └── task_bind ────────────────> task complete
```

## 任务新字段

```json
{
  "worktree": "auth-refactor",
  "worktree_state": "active",  // unbound/active/kept/removed
  "closeout": {"action": "keep", "reason": "", "at": 123456}
}
```

## 工具接口

### 任务工具 (4个)

| 工具 | 功能 |
|------|------|
| `task_create` | 创建任务 |
| `task_list` | 列出任务 |
| `task_get` | 获取详情 |
| `task_bind_worktree` | 绑定到 worktree |

### Worktree 工具 (8个)

| 工具 | 功能 |
|------|------|
| `worktree_create` | 创建 worktree |
| `worktree_list` | 列出所有 |
| `worktree_enter` | 进入 worktree |
| `worktree_status` | git 状态 |
| `worktree_run` | 执行命令 |
| `worktree_closeout` | 关闭 (keep/remove) |
| `worktree_keep` | 保留 |
| `worktree_remove` | 删除 |

## 目录结构

```
.worktrees/
├── index.json              # Worktree 注册表
├── events.jsonl            # 生命周期事件
└── feature-a/             # 独立工作目录
    └── (代码文件)

.tasks/
├── task_1.json             # 任务记录
├── task_2.json
└── ...
```

## 模块对比

| 模块 | 主题 | 隔离方式 |
|------|------|---------|
| s12 | 任务系统 | 无目录隔离 |
| s15-17 | 团队协作 | 进程/消息隔离 |
| **s18** | **Worktree** | **目录级并行** |

## 测试方法

```bash
python s18_worktree_isolation.py
```

### 前提条件

需要在 git 仓库中运行，否则 `worktree_*` 工具会报错。

### 基本命令

```
# 查看任务
s18 >> 列出所有任务

# 查看 worktree
s18 >> 列出所有 worktree
```

### 场景测试

**1. 创建任务 + Worktree**
```
s18 >> 创建任务：重构认证模块
s18 >> 创建 worktree：name=auth-refactor, task_id=1
```

**2. 在 worktree 中工作**
```
s18 >> 在 worktree auth-refactor 中执行：git status
s18 >> 在 worktree auth-refactor 中执行：ls -la
```

**3. 保留 worktree**
```
s18 >> 保留 worktree：name=auth-refactor, reason="需要后续集成"
```

**4. 删除 worktree + 完成任务**
```
s18 >> 关闭 worktree：name=auth-refactor, action=remove, complete_task=true
```

### 手动验证

```bash
# 查看 worktree 索引
cat .worktrees/index.json

# 查看事件日志
cat .worktrees/events.jsonl

# 查看任务绑定
cat .tasks/task_1.json

# 查看实际 worktree 目录
ls -la .worktrees/
```

### Git Worktree 命令 (底层)

```bash
# 列出所有 worktree
git worktree list

# 创建 worktree
git worktree add -b wt/feature-a ../.worktrees/feature-a HEAD

# 移除 worktree
git worktree remove ../.worktrees/feature-a
```

## 核心设计思想

1. **控制/执行分离**: 任务管理控制流，worktree 管理执行
2. **目录隔离**: 每个 worktree 是独立目录，不会冲突
3. **可观测性**: EventBus 记录所有生命周期事件
4. **显式关闭**: 必须显式 keep/remove，不能遗留

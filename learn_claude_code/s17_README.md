# s17 - Autonomous Agents

自主智能体，支持自动从任务板认领工作、IDLE 轮询循环、身份重注入。构建在 s12 任务板、s15 团队消息、s16 协议之上。

## 核心概念

**自主队友** - 无需显式分配任务，可自动从任务板认领工作并执行。

```
s12: TaskManager (手动管理)
s15: TeammateManager (持久化成员)
s16: + RequestStore (协议握手)
s17: + 自主认领 + IDLE 循环 + 身份重注入
```

## 生命周期图

```
┌────────┐
│ spawn  │
└────┬───┘
     │
     v
┌────────┐  tool_use   ┌────────┐
│ WORK   │ <----------- │  LLM   │
└───┬────┘              └────────┘
    │
    | stop_reason != tool_use
    v
┌────────┐ poll every 5s for 60s
│ IDLE   │ ──> check inbox -> message? -> resume WORK
│        │ ──> scan .tasks/ -> unclaimed? -> claim -> resume WORK
└───┬────┘ ──> timeout (60s) -> shutdown
```

## 三大新特性

| 特性 | 功能 | 实现 |
|------|------|------|
| **IDLE 循环** | 无工作时轮询收件箱和任务板 | `idle` 工具 + POLL_INTERVAL=5s |
| **自动认领** | 扫描并认领未分配任务 | `scan_unclaimed_tasks()` + `claim_task()` |
| **身份重注入** | 上下文压缩后恢复身份 | `ensure_identity_context()` |

## 组件说明

### 任务认领

```python
is_claimable_task(task):
  - status == "pending"       # 任务等待中
  - no owner                  # 未被认领
  - no blockedBy             # 无前置依赖
  - claim_role 匹配          # 可选角色限制
```

### 身份重注入

```python
# 压缩后插入身份块
messages = [
  {"role": "user", "content": "<identity>You are 'alice', role: coder, team: my-team...</identity>"},
  {"role": "assistant", "content": "I am alice. Continuing."},
  ...remaining messages...
]
```

### Claim 事件记录

```
.tasks/claim_events.jsonl
{"event": "task.claimed", "task_id": 1, "owner": "alice", "role": "coder", "source": "auto", "ts": 1234567890}
```

## 与 s16 对比

| 特性 | s16 | s17 |
|------|-----|-----|
| 团队管理 | ✓ | ✓ |
| 协议握手 | ✓ | ✓ |
| MessageBus | ✓ | ✓ |
| RequestStore | ✓ | ✓ |
| IDLE 循环 | ✗ | ✓ |
| 自动认领 | ✗ | ✓ |
| 身份重注入 | ✗ | ✓ |
| 任务板集成 | ✗ | ✓ |

## 工具扩展

| 新增工具 | 功能 |
|----------|------|
| `idle` | 标记无工作，进入空闲轮询 |
| `claim_task` | 手动认领任务 |

## 目录结构

```
.tokens/               # 任务文件
├── task_1.json        # 任务记录
├── task_2.json
└── claim_events.jsonl  # 认领事件日志

.team/                 # 团队文件
├── config.json        # 成员配置
├── inbox/             # 消息收件箱
└── requests/          # 协议请求
```

## 模块对比

| 模块 | 主题 | 核心功能 |
|------|------|---------|
| s12 | 任务系统 | 手动任务管理 |
| s13 | 后台任务 | 运行时执行槽 |
| s14 | 定时调度 | cron 表达式 |
| s15 | 多智能体团队 | 持久化队友 |
| s16 | 团队协议 | shutdown/plan approval |
| **s17** | **自主智能体** | **自动认领 + IDLE 循环** |

## 测试方法

```bash
python s17_autonomous_agents.py
```

### 基本命令

```
# 查看团队
s17 >> /team

# 查看任务板
s17 >> /tasks

# 查看收件箱
s17 >> /inbox

# 退出
s17 >> q
```

### 场景测试

**1. 产生自主队友**
```
s17 >> 产生一个叫 coder 的队友，角色是 developer，任务是写代码
```

**2. 验证自动认领**
```bash
# 创建任务
mkdir -p .tasks
echo '{"id": 1, "subject": "实现登录功能", "status": "pending"}' > .tasks/task_1.json
```

```
# coder 应自动认领
s17 >> /team
# coder 状态变为 working

s17 >> /tasks
# 任务 1 状态变为 in_progress，owner=coder
```

**3. 手动认领任务**
```
s17 >> 认领任务 2
```

**4. 发送消息给队友**
```
s17 >> 发消息给 coder：检查一下代码
```

**5. 关闭超时测试**
```
# 等待 60s 不操作，队友应自动关闭
s17 >> /team
# coder 状态变为 shutdown
```

**6. 角色匹配测试**
```bash
# 创建有角色要求的任务
echo '{"id": 3, "subject": "前端开发", "claim_role": "frontend", "status": "pending"}' > .tasks/task_3.json
echo '{"id": 4, "subject": "后端开发", "claim_role": "backend", "status": "pending"}' > .tasks/task_4.json
```

```
# 产生不同角色的队友
s17 >> 产生 alice，角色是 frontend
s17 >> 产生 bob，角色是 backend

# 观察按角色分配
s17 >> /tasks
# alice 认领 task_3，bob 认领 task_4
```

### 手动验证

```bash
# 查看认领事件
cat .tasks/claim_events.jsonl

# 查看任务状态
cat .tasks/task_1.json

# 查看团队状态
cat .team/config.json
```

### 调试技巧

```bash
# 观察线程输出
python s17_autonomous_agents.py 2>&1

# 查看所有 JSON 文件
find .tasks -name "*.json" -exec echo "=== {} ===" \; -exec cat {} \;
```

## 核心设计思想

1. **WORK/IDLE 双状态**: 工作状态执行任务，空闲状态轮询新任务
2. **被动触发**: 队友不等待显式分配，自己找活干
3. **角色匹配**: 支持按角色分配任务
4. **超时关闭**: 空闲超时后自动 shutdown
5. **身份保留**: 上下文压缩后重注入身份信息

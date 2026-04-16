# s16 - Team Protocols

结构化握手协议，基于 s15 的消息总线添加持久化请求/响应模式。

## 核心概念

**协议握手** - 通过 `request_id` 关联请求和响应，实现可靠的团队协作流程。

```
s15: MessageBus (JSONL inbox) -> 基础消息通信
s16: + RequestStore (.team/requests/*.json) -> 持久化协议状态
```

## 两大协议

| 协议 | 用途 | FSM 状态 |
|------|------|----------|
| **Shutdown** | 优雅关闭队友 | `pending → approved / rejected` |
| **Plan Approval** | 计划审批 | `pending → approved / rejected` |

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: MessageBus (JSONL inbox)                           │
│  .team/inbox/{name}.jsonl                                   │
│  -> 实时消息传递                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: RequestStore (持久化请求)                         │
│  .team/requests/{request_id}.json                           │
│  -> 协议握手状态，跨消息持久化                               │
└─────────────────────────────────────────────────────────────┘

Shutdown Protocol:
┌──────────────┐         ┌──────────────┐
│ shutdown_req  │ ──────> │ 收到请求      │
│ {request_id}  │         │ 决定 approve │
└──────────────┘         └──────┬───────┘
       ^                        │
       │                        v
┌──────────────┐         ┌──────────────┐
│ shutdown_resp│ <────── │ response     │
│ {approve}    │         │ {approve}    │
└──────────────┘         └──────────────┘
       |
       v
  状态写入 RequestStore

Plan Approval Protocol:
┌──────────────┐         ┌──────────────┐
│ plan_approval │ ──────> │ 审查计划      │
│ {plan, req_id}│         │ approve/rej  │
└──────────────┘         └──────┬───────┘
       ^                        │
       │                        v
┌──────────────┐         ┌──────────────┐
│ approval_resp│ <────── │ 响应审批     │
└──────────────┘         └──────────────┘
```

## 三大组件

| 组件 | 功能 | 文件位置 |
|------|------|----------|
| `MessageBus` | JSONL 收件箱，读写消息 | 第 86-131 行 |
| `RequestStore` | 持久化请求记录 | 第 137-175 行 |
| `TeammateManager` | 成员管理与线程控制 | 第 179-428 行 |

### MessageBus

```python
# 发送消息 -> 追加到 .team/inbox/{to}.jsonl
BUS.send(sender, to, content, msg_type="message")

# 读取收件箱 -> drain 模式
BUS.read_inbox(name)

# 广播
BUS.broadcast(sender, content, teammates)
```

### RequestStore

```json
// .team/requests/{request_id}.json
{
  "request_id": "abc12345",
  "kind": "shutdown | plan_approval",
  "from": "alice",
  "to": "lead",
  "status": "pending | approved | rejected",
  "plan": "...",           // plan_approval 特有
  "created_at": 1234567890,
  "updated_at": 1234567890
}
```

**特点**: 消息发送后，请求记录仍持久化，支持事后检查/恢复/协调

## 协议工具

### Lead 工具

| 工具 | 功能 |
|------|------|
| `spawn_teammate` | 产生队友 |
| `list_teammates` | 列出队友 |
| `send_message` | 发消息 |
| `read_inbox` | 读取收件箱 |
| `broadcast` | 广播 |
| `shutdown_request` | 发送关闭请求（返回 request_id） |
| `shutdown_response` | 查看关闭请求状态 |
| `plan_approval` | 审批计划（approve + feedback） |

### Teammate 工具

| 工具 | 功能 |
|------|------|
| `send_message` | 发消息给其他队友 |
| `read_inbox` | 读取自己的收件箱 |
| `shutdown_response` | 响应关闭请求 |
| `plan_approval` | 提交计划等待审批 |

## 消息类型

```python
VALID_MSG_TYPES = {
    "message",               # 普通消息
    "broadcast",            # 广播
    "shutdown_request",      # 关闭请求
    "shutdown_response",     # 关闭响应
    "plan_approval",        # 计划审批
    "plan_approval_response" # 计划响应
}
```

## 目录结构

```
.team/
├── config.json              # 团队配置
├── inbox/
│   ├── lead.jsonl           # Lead 收件箱
│   ├── alice.jsonl          # Alice 收件箱
│   └── bob.jsonl
└── requests/
    ├── {req_id1}.json       # 持久化请求
    └── {req_id2}.json
```

## 与 s15 对比

| 特性 | s15 | s16 |
|------|-----|-----|
| MessageBus | ✓ | ✓ |
| TeammateManager | ✓ | ✓ |
| 持久化成员 | ✓ | ✓ |
| RequestStore | ✗ | ✓ |
| Shutdown Protocol | ✗ | ✓ |
| Plan Approval | ✗ | ✓ |

## 模块对比

| 模块 | 主题 | 存储 |
|------|------|------|
| s12 | 任务系统 | `.tasks/*.json` |
| s13 | 后台任务 | `.runtime-tasks/*.json` |
| s14 | 定时调度 | `.claude/scheduled_tasks.json` |
| s15 | 多智能体团队 | `.team/config.json + inbox/*.jsonl` |
| **s16** | **团队协议** | **`.team/requests/*.json`** |

## 测试方法

```bash
python s16_team_protocols.py
```

### 基本命令

```
# 查看团队
s16 >> /team

# 查看收件箱
s16 >> /inbox

# 退出
s16 >> q
```

### 场景测试

**1. 产生队友**
```
s16 >> 产生一个叫 dev 的队友，角色是 developer，任务是写一个加法函数
```

**2. 发送关闭请求**
```
s16 >> 发送关闭请求给 dev
```

**3. 查看请求持久化**
```bash
cat .team/requests/{req_id}.json
# status: "pending"
```

**4. 等待队友响应后**
```bash
cat .team/requests/{req_id}.json
# status: "approved" 或 "rejected"
```

**5. 计划审批流程**
```
# 队友发送计划
s16 >> 发消息给 dev：请提交工作计划

# 查看收件箱
s16 >> /inbox
# 应看到 plan_approval 请求

# 审批计划
s16 >> 审批计划请求 abc12345，approve=true，反馈：方案可行
```

### 手动验证

```bash
# 查看所有请求
ls -la .team/requests/

# 查看特定请求详情
cat .team/requests/abc12345.json

# 查看消息
cat .team/inbox/dev.jsonl
```

## 核心设计思想

1. **两层消息**: MessageBus 负责实时通信，RequestStore 负责持久化状态
2. **request_id 关联**: 请求和响应通过唯一 ID 关联
3. **状态机流转**: pending → approved/rejected，支持追踪
4. **协议可扩展**: 同一模式可支持更多协议类型

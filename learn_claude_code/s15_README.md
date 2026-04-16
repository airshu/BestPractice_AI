# s15 - Agent 团队系统 (Agent Teams)

## 概述

`s15_agent_teams.py` 演示了多智能体团队协作机制。多个持久化命名 Agent 通过文件-based JSONL 收件箱进行通信，每个队友在独立线程中运行自己的工作循环。

## 核心概念

| 概念 | 说明 |
|------|------|
| Subagent (s04) | spawn -> execute -> return -> destroyed（一次性） |
| Teammate (s15) | spawn -> work -> idle -> work -> ... -> shutdown（持久化） |

## 架构图

```
.team/config.json                   .team/inbox/
+----------------------------+      +------------------+
| {"team_name": "default",   |      | alice.jsonl      |
|  "members": [              |      | bob.jsonl        |
|    {"name":"alice",        |      | lead.jsonl       |
|     "role":"coder",        |      +------------------+
|     "status":"idle"}       |
|  ]}                        |
+----------------------------+

spawn_teammate("alice","coder",...)
         |
         v
    Thread: alice             Thread: bob
    +------------------+      +------------------+
    | agent_loop       |      | agent_loop       |
    | status: working  |      | status: idle     |
    | ... runs tools   |      | ... waits ...    |
    | status -> idle   |      |                  |
    +------------------+      +------------------+
```

## 三大核心组件

| 组件 | 功能 |
|------|------|
| `MessageBus` | JSONL 收件箱，读写消息文件 |
| `TeammateManager` | 持久化成员注册表 + 线程启动器 |
| `_teammate_loop` | 每个队友的独立工作循环 |

### MessageBus

```python
# 发送消息 -> 追加到 .team/inbox/{to}.jsonl
BUS.send(sender, to, content, msg_type="message")

# 读取收件箱 -> 读取后清空文件（drain 模式）
BUS.read_inbox(name)

# 广播给所有队友
BUS.broadcast(sender, content, teammates)
```

### 消息类型

| 类型 | 说明 |
|------|------|
| `message` | 普通消息 |
| `broadcast` | 广播消息 |
| `shutdown_request` | 关闭请求 |
| `shutdown_response` | 关闭响应 |
| `plan_approval` | 计划审批 |
| `plan_approval_response` | 计划审批响应 |

### TeammateManager

| 方法 | 功能 |
|------|------|
| `spawn()` | 创建/唤醒队友，启动线程 |
| `list_all()` | 列出所有成员 |
| `member_names()` | 获取成员名列表 |

### 队友状态机

```
working -> idle -> working -> ... -> shutdown
```

## 工具接口

### Lead（团队领导）工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `spawn_teammate` | name, role, prompt | 产生队友 |
| `list_teammates` | - | 列出队友 |
| `send_message` | to, content, msg_type | 发消息 |
| `read_inbox` | - | 读取收件箱 |
| `broadcast` | content | 广播消息 |

### Teammate（队友）工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `send_message` | to, content, msg_type | 发消息给其他队友 |
| `read_inbox` | - | 读取自己的收件箱 |

## 持久化结构

### config.json

```json
{
  "team_name": "default",
  "members": [
    {"name": "alice", "role": "coder", "status": "idle"},
    {"name": "bob", "role": "reviewer", "status": "working"}
  ]
}
```

### inbox/*.jsonl

```jsonl
{"type": "message", "from": "lead", "content": "检查代码", "timestamp": 1234567890.0}
{"type": "broadcast", "from": "alice", "content": "任务完成", "timestamp": 1234567891.0}
```

## 与 s04 对比

| 特性 | s04 Subagent | s15 Teammate |
|------|-------------|-------------|
| 生命周期 | 一次性 | 持久化 |
| 通信方式 | 返回结果 | 消息队列 |
| 状态管理 | 无状态 | 有状态 (working/idle) |
| 线程管理 | 用完销毁 | 保持/复用 |
| 适用场景 | 独立任务 | 协作任务 |

## 测试方法

```bash
python s15_agent_teams.py
```

### 基本命令

```
# 列出团队成员
s15 >> /team

# 查看收件箱
s15 >> /inbox

# 退出
s15 >> q
```

### 交互示例

```
# 1. 产生队友
s15 >> 产生一个叫 alice 的队友，角色是 coder，任务是写一个 hello world 函数

# 2. 产生多个队友
s15 >> 产生两个队友：bob 是 reviewer，carol 是 tester

# 3. 发送消息
s15 >> 发消息给 alice：检查一下你写的代码

# 4. 广播
s15 >> 广播消息：会议将在5分钟后开始

# 5. 查看状态
s15 >> /team
```

### 手动验证

```bash
# 查看团队配置
cat .team/config.json

# 查看收件箱内容
cat .team/inbox/alice.jsonl

# 查看所有收件箱
ls -la .team/inbox/
```

## 目录结构

```
learn_claude_code/
├── .team/
│   ├── config.json          # 团队配置
│   └── inbox/
│       ├── lead.jsonl       # Lead 收件箱
│       ├── alice.jsonl      # Alice 收件箱
│       └── bob.jsonl        # Bob 收件箱
├── s15_agent_teams.py
└── s15_README.md
```

## 与其他模块对比

| 模块 | 协作方式 | 持久化 |
|------|---------|--------|
| s12 任务系统 | 单 Agent 任务管理 | 磁盘 |
| s13 后台任务 | 单 Agent 异步执行 | 磁盘 |
| s14 定时调度 | 单 Agent 时间驱动 | 可选 |
| **s15 Agent 团队** | **多 Agent 通信协作** | **内存+磁盘** |

## 注意事项

1. **线程安全**: 使用文件锁避免并发写入冲突
2. **Drain 模式**: `read_inbox` 读取后自动清空文件
3. **Daemon 线程**: 队友线程在主进程退出时自动终止
4. **收件箱路径**: `.team/inbox/{name}.jsonl`

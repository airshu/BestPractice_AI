# s04 - 子 Agent 与上下文隔离 (Subagents)

## 概述

`s04_subagent.py` 演示了子 Agent 机制。子 Agent 拥有独立的 fresh messages=[] 上下文，共享文件系统，但返回时只有摘要而非完整历史。

## 核心洞察

> "Fresh messages=[] 提供了上下文隔离。父上下文保持干净。"

## 架构图

```
父 Agent                           子 Agent
+------------------+               +------------------+
| messages=[...]   |   dispatch    | messages=[]      |  <-- fresh
|                  |  ----------> |                  |
| tool: task       |              | while tool_use:  |
|   prompt="..."   |              |   call tools     |
|   description="" |              |   append results |
|                  |   summary    |                  |
|   result = "..." | <----------  | return last text |
+------------------+               +------------------+
      │
      │ 父上下文保持干净
      │ 子上下文被丢弃
```

## run_subagent 流程

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]  # fresh context
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL,
            system=SUBAGENT_SYSTEM,
            messages=sub_messages,      # fresh = []
            tools=CHILD_TOOLS,          # 过滤的工具集
            max_tokens=8000,
        )
        sub_messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        # 执行工具...
    # 只有最终文本返回给父 Agent
    return "".join(b.text for b in response.content if hasattr(b, "text"))
```

## 工具分层

| 工具 | 父 Agent | 子 Agent |
|------|----------|----------|
| bash | ✓ | ✓ |
| read_file | ✓ | ✓ |
| write_file | ✓ | ✓ |
| edit_file | ✓ | ✓ |
| task | ✓ | ✗ (禁止递归) |

## AgentTemplate 类

解析 Markdown frontmatter 中的 Agent 定义：

```markdown
---
name: coder
tools: [bash, read_file, write_file]
---

You are a coding agent...
```

## 与 s15 Agent 团队的区别

| 特性 | s04 Subagent | s15 Teammate |
|------|-------------|-------------|
| 生命周期 | 一次性 | 持久化 |
| 上下文 | fresh (每次新建) | 保持 idle 状态 |
| 通信 | 摘要返回 | 消息队列 |
| 状态 | 无 | 有 (working/idle) |

## 真实 Claude Code 对比

| 方面 | 本演示 | 真实 Claude Code |
|------|--------|-----------------|
| 后端 | 仅 in-process | 5 种：in-process/tmux/iTerm2/fork/remote |
| 上下文隔离 | fresh messages=[] | createSubagentContext() 隔离 20+ 字段 |
| 工具过滤 | 手动过滤 | resolveAgentTools() |
| Agent 定义 | 硬编码 system prompt | .claude/agents/*.md |

## 测试方法

```bash
python s04_sub_agent.py
```

### 交互示例

```
s04 >> 启动子 Agent：探索项目结构，列出所有 Python 文件

========== SUBAGENT STARTED ==========
[SUBAGENT] Task: 探索项目结构...
[SUBAGENT] Turn 1...
> read_file: ./s01_agent_loop.py
...
[SUBAGENT] Finished, returning summary
========== SUBAGENT ENDED ==========

s04 >> 使用子 Agent 查找所有 TODO 注释

s04 >> q
```

### 测试上下文隔离

1. 在子 Agent 中执行多个操作
2. 观察子 Agent 上下文被丢弃
3. 父 Agent 只有摘要，不包含完整历史

## 目录结构

```
learn_claude_code/
├── .claude/
│   └── agents/              # Agent 定义目录
├── s04_subagent.py
└── s04_README.md
```

# s01 - Agent 循环基础 (The Agent Loop)

## 概述

`s01_agent_loop.py` 是最小的可用编码 Agent 模式。演示了 Agent 循环的基本结构：用户输入 -> 模型回复 -> 执行工具 -> 循环继续。

## 核心流程

```
用户消息 (user message)
    │
    ▼
模型回复 (model reply)
    │
    ├── stop_reason != "tool_use" ──> 结束
    │
    ▼
执行工具调用 (execute tool_use)
    │
    ▼
写入 tool_result 回消息列表
    │
    └── 继续循环
```

## 核心概念

| 概念 | 说明 |
|------|------|
| LoopState | 循环状态：消息历史、轮次计数、转换原因 |
| stop_reason | 决定是否继续：tool_use 继续，其他结束 |
| tool_use | 模型的工具调用请求 |
| tool_result | 工具执行结果，返回给模型 |

## LoopState 数据类

```python
@dataclass
class LoopState:
    messages: list           # 对话历史
    turn_count: int = 1     # 轮次计数
    transition_reason: str | None = None  # 继续原因
    debug: bool = False      # 调试模式
```

## 工具接口

| 工具 | 参数 | 说明 |
|------|------|------|
| `bash` | command | 运行 shell 命令 |

## 危险命令拦截

```python
dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
```

## 调试模式

```bash
python s01_agent_loop.py --debug
```

启用后输出：
- 每轮 latencies
- stop_reason
- tool_calls

## 测试方法

```bash
python s01_agent_loop.py
```

### 交互示例

```
s01 >> 列出当前目录文件
$ ls -la
total 48
drwxr-xr-x ... file1.txt
...

s01 >> 显示当前时间
$ date
2024-01-15 10:30:00

s01 >> q
```

### 测试危险命令拦截

```
s01 >> 删除根目录
Error: Dangerous command blocked
```

## 与后续章节的关系

- s01: 基础循环
- s02: 添加更多工具
- s03: 添加 todo 规划
- s04: 添加子 Agent
- s05: 添加 skill 加载
- s06: 添加上下文压缩

## 文件结构

```
learn_claude_code/
├── s01_agent_loop.py    # 主脚本
├── s01_README.md        # 本文档
└── ...
```

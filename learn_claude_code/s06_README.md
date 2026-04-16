# s06 - 上下文压缩 (Context Compact)

## 概述

`s06_context_compact.py` 演示了三层上下文压缩机制，确保对话上下文保持在可用范围内：

1. 大输出持久化到磁盘
2. 旧工具结果微压缩
3. 整体对话摘要

## 三层压缩策略

```
┌─────────────────────────────────────────────────────────────┐
│                     上下文大小                               │
│                                                             │
│  > 50000 chars ──> [自动压缩] ──> summarize_history()       │
│                                                             │
│  工具结果 > 3 个 ──> [微压缩] ──> 保留最近，替换旧结果        │
│                                                             │
│  输出 > 30000 chars ──> [持久化] ──> 写入磁盘，返回预览      │
└─────────────────────────────────────────────────────────────┘
```

## 核心常量

| 常量 | 值 | 说明 |
|------|-----|------|
| CONTEXT_LIMIT | 50000 | 自动压缩阈值 |
| KEEP_RECENT_TOOL_RESULTS | 3 | 保留最近工具结果数 |
| PERSIST_THRESHOLD | 30000 | 大输出持久化阈值 |
| PREVIEW_CHARS | 2000 | 预览字符数 |

## 核心数据结构

### CompactState

```python
@dataclass
class CompactState:
    has_compacted: bool = False    # 是否已压缩过
    last_summary: str = ""          # 最后摘要
    recent_files: list[str] = []   # 最近访问文件
```

## 三大压缩函数

### 1. persist_large_output()

大输出持久化到磁盘，返回预览：

```python
def persist_large_output(tool_use_id: str, output: str) -> str:
    if len(output) <= PERSIST_THRESHOLD:
        return output
    # 写入 .task_outputs/tool-results/{tool_use_id}.txt
    return (
        "<persisted-output>\n"
        f"Full output saved to: {rel_path}\n"
        "Preview:\n"
        f"{preview}\n"
        "</persisted-output>"
    )
```

### 2. micro_compact()

微压缩旧工具结果：

```python
def micro_compact(messages: list) -> list:
    tool_results = collect_tool_result_blocks(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS:
        return messages
    for _, _, block in tool_results[:-KEEP_RECENT_TOOL_RESULTS]:
        block["content"] = "[Earlier tool result compacted.]"
    return messages
```

### 3. compact_history()

整体对话摘要：

```python
def compact_history(messages: list, state: CompactState) -> list:
    # 1. 保存转录到磁盘
    transcript_path = write_transcript(messages)
    # 2. LLM 生成摘要
    summary = summarize_history(messages)
    # 3. 返回压缩后的单一消息
    return [{
        "role": "user",
        "content": f"This conversation was compacted.\n\n{summary}"
    }]
```

## summarize_history() 摘要提示

```python
prompt = """Summarize this coding-agent conversation so work can continue.
Preserve:
1. The current goal
2. Important findings and decisions
3. Files read or changed
4. Remaining work
5. User constraints and preferences
Be compact but concrete."""
```

## 工具接口

| 工具 | 参数 | 说明 |
|------|------|------|
| `compact` | focus | 手动压缩对话（可选焦点） |

## agent_loop 中的压缩流程

```python
def agent_loop(messages, state):
    while True:
        # 1. 微压缩
        messages[:] = micro_compact(messages)
        
        # 2. 自动压缩检查
        if estimate_context_size(messages) > CONTEXT_LIMIT:
            print("[auto compact]")
            messages[:] = compact_history(messages, state)
        
        # 3. LLM 调用...
        
        # 4. 手动压缩检查
        if manual_compact:
            messages[:] = compact_history(messages, state, focus=focus)
```

## 持久化目录

```
.task_outputs/
  tool-results/
    {tool_use_id}.txt    # 大输出存储
.transcripts/
  transcript_{timestamp}.jsonl  # 对话转录
```

## 与 s11 错误恢复的区别

| 特性 | s06 压缩 | s11 恢复 |
|------|----------|----------|
| 触发条件 | 上下文过大 | 错误发生 |
| 处理方式 | LLM 摘要 | 续写/压缩/重试 |
| 位置 | 主动 | 被动 |
| 目的 | 保持可用上下文 | 处理异常 |

## 测试方法

```bash
python s06_context_compact.py
```

### 测试微压缩

1. 执行多个命令，积累超过 3 个工具结果
2. 观察旧结果被替换为 `[Earlier tool result compacted.]`

### 测试大输出持久化

1. 执行产生大量输出的命令（如 `find / -name "*.py"`）
2. 观察输出被持久化到磁盘

### 测试自动压缩

1. 持续对话，直到上下文超过 50000 chars
2. 观察 `[auto compact]` 输出

### 测试手动压缩

```
s06 >> compact focus="保持文件列表"
```

## 目录结构

```
learn_claude_code/
├── .task_outputs/
│   └── tool-results/        # 大输出存储
├── .transcripts/            # 对话转录
├── s06_context_compact.py
└── s06_README.md
```

## 优势

1. **防止上下文溢出**: 保持对话可用
2. **节省 Token**: 压缩后上下文更小
3. **可追溯**: 转录和输出持久化到磁盘
4. **可恢复**: 摘要保留关键信息

# s02 - 工具调度与消息规范化 (Tool Dispatch)

## 概述

`s02_tool_use.py` 扩展了 s01 的工具集，从单一 bash 工具扩展到文件读写编辑工具，并添加了 `normalize_messages()` 函数来规范化消息格式。

**核心洞察**: "循环本身没有变化，只是添加了工具。"

## 架构图

```
normalize_messages() 处理流程:
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 原始消息     │ -> │ 1. 清理元数据    │ -> │ 2. 插入缺失结果  │
└─────────────┘    └──────────────────┘    └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ 3. 合并同角色消息 │
                                    └─────────────────┘
```

## 工具集

| 工具 | 参数 | 说明 |
|------|------|------|
| `bash` | command | 运行 shell 命令 |
| `read_file` | path, limit | 读取文件内容 |
| `write_file` | path, content | 写入文件 |
| `edit_file` | path, old_text, new_text | 精确文本替换 |

## normalize_messages() 三大职责

### 1. 清理元数据

```python
# 移除 API 不理解的内部字段
clean["content"] = [
    {k: v for k, v in block.items() if not k.startswith("_")}
    for block in msg["content"]
]
```

### 2. 插入缺失的工具结果

```python
# 查找孤立的 tool_use，插入占位符结果
if block.get("type") == "tool_use" and block["id"] not in existing_results:
    cleaned.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": block["id"], "content": "(cancelled)"}]
    })
```

### 3. 合并同角色消息

```python
# API 要求严格的消息交替
# 合并连续的相同 role 消息
if msg["role"] == merged[-1]["role"]:
    prev["content"] = prev_c + curr_c
```

## 并发安全分类

```python
CONCURRENCY_SAFE = {"read_file"}      # 可并行执行
CONCURRENCY_UNSAFE = {"write_file", "edit_file"}  # 必须串行
```

## 路径安全

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path
```

## 测试方法

```bash
python s02_tool_use.py
```

### 交互示例

```
s02 >> 读取当前目录
> read_file:
total 32
drwxr-xr-x ... s01_agent_loop.py
...

s02 >> 写一个测试文件
> write_file:
Wrote 15 bytes to test.txt

s02 >> 编辑文件
> edit_file:
Edited test.txt

s02 >> q
```

### 测试完整流程

```
s02 >> 创建一个 Python 文件：路径 hello.py，内容是打印 hello world

s02 >> 读取文件确认内容

s02 >> 编辑文件：把 hello world 改成 hello Claude

s02 >> 运行文件确认执行结果
```

## 与 s01 的区别

| 特性 | s01 | s02 |
|------|-----|-----|
| 工具数量 | 1 (bash) | 4 (bash/read/write/edit) |
| 消息规范化 | 无 | normalize_messages() |
| 路径安全 | 无 | safe_path() |
| 并发分类 | 无 | CONCURRENCY_SAFE/UNSAFE |

## 目录结构

```
learn_claude_code/
├── .transcripts/           # 脚本记录目录
├── .task_outputs/         # 任务输出目录
├── s02_tool_use.py
└── s02_README.md
```

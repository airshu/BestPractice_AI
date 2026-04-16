# s11 - 错误恢复系统 (Error Recovery)

## 概述

`s11_error_recovery.py` 演示了一个具有韧性的 AI Agent 如何在各种错误情况下优雅恢复，而不是崩溃。

## 三种恢复策略

```
LLM 响应
   │
   v
[检查 stop_reason]
   │
   ├── "max_tokens" ────> [策略1: 输出截断恢复]
   │                      注入继续消息，重试（最多3次）
   │
   ├── API 错误 ─────────> [策略2: 上下文压缩恢复]
   │                      当 prompt_too_long 时，触发 auto_compact
   │                      用 LLM 生成摘要替换历史
   │
   ├── 网络错误 ─────────> [策略3: 指数退避重试]
   │                      连接/速率错误，使用指数退避
   │                      base * 2^attempt + jitter
   │
   └── "end_turn" ───────> [正常退出]
```

## 恢复优先级

1. **max_tokens 截断** → 注入继续消息，重试
2. **prompt_too_long** → 压缩上下文，重试
3. **连接错误** → 退避等待，重试
4. **所有重试耗尽** → 优雅失败

## 核心常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `MAX_RECOVERY_ATTEMPTS` | 3 | 最大重试次数 |
| `MAX_OUTPUT_TOKENS` | 2000 | 输出 token 限制 |
| `BACKOFF_BASE_DELAY` | 1.0s | 退避基础延迟 |
| `BACKOFF_MAX_DELAY` | 30.0s | 退避最大延迟 |
| `TOKEN_THRESHOLD` | 50000 | 自动压缩阈值 |

## 策略详解

### 策略1: max_tokens 恢复

当输出被截断时：
```python
CONTINUATION_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped -- "
    "no recap, no repetition. Pick up mid-sentence if needed."
)
```

**流程**:
1. 检测 `stop_reason == "max_tokens"`
2. 注入继续消息
3. 重试（最多3次）
4. 仍失败则报告错误

### 策略2: 上下文压缩 (auto_compact)

当 prompt 过长时，使用 LLM 生成摘要：

```python
def auto_compact(messages: list) -> list:
    # 1. 提取对话文本
    conversation_text = json.dumps(messages, default=str)[:80000]
    
    # 2. 让 LLM 生成摘要
    prompt = """Summarize this conversation for continuity. Include:
    1) Task overview and success criteria
    2) Current state: completed work, files touched
    3) Key decisions and failed approaches
    4) Remaining next steps"""
    
    # 3. 返回压缩后的上下文
    return [{"role": "user", "content": f"Summary: {summary}\n\nContinue..."}]
```

**主动压缩**: 当 token 估计超过阈值时，也会主动压缩：
```python
if estimate_tokens(messages) > TOKEN_THRESHOLD:
    messages[:] = auto_compact(messages)
```

### 策略3: 指数退避重试

处理临时性网络错误：
```python
def backoff_delay(attempt: int) -> float:
    delay = min(BACKOFF_BASE_DELAY * (2**attempt), BACKOFF_MAX_DELAY)
    jitter = random.uniform(0, 1)  # 添加随机性避免雷群
    return delay + jitter
```

**延迟序列**: 1s → 2s → 4s (+ 随机抖动)

## 错误类型处理

| 错误类型 | 处理方式 |
|---------|---------|
| `APIError: overlong_prompt` | 压缩上下文后重试 |
| `APIError: rate_limit` | 指数退避重试 |
| `ConnectionError` | 指数退避重试 |
| `TimeoutError` | 指数退避重试 |

## 调试输出

启用调试日志查看恢复过程：
```python
print(f"[DEBUG] stop_reason: {response.stop_reason}")
print(f"[DEBUG] tokens: input={response.usage.input_tokens}, output={response.usage.output_tokens}")
print(f"[Recovery] max_tokens hit ({count}/{MAX_RECOVERY_ATTEMPTS}). Injecting continuation...")
print(f"[Recovery] API error: {e}. Retrying in {delay:.1f}s...")
```

## 测试方法

```bash
# 正常测试
python s11_error_recovery.py

# 测试 max_tokens 恢复（设置小值）
# 修改 MAX_OUTPUT_TOKENS = 100

# 测试提示
s11 >> 写一个很长的Python程序，包含100个函数

# 退出
s11 >> q
```

## 与 s06_context_compact 的区别

| 特性 | s06 | s11 |
|------|-----|-----|
| 压缩触发 | 手动 `compact` 消息 | 自动检测 + 错误驱动 |
| 恢复策略 | 仅压缩 | max_tokens + 压缩 + 退避 |
| 退避机制 | 无 | 指数退避重试 |
| 适用场景 | 主动管理 | 被动容错 |

## 生产建议

1. **MAX_OUTPUT_TOKENS**: 测试用 2000，生产环境改为 8000
2. **TOKEN_THRESHOLD**: 根据模型上下文窗口调整
3. **BACKOFF_MAX_DELAY**: 根据服务 SLA 调整
4. **日志记录**: 添加持久化日志用于监控恢复频率

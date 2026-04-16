# s13 - 后台任务系统 (Background Tasks)

## 概述

`s13_background_tasks.py` 演示了后台任务执行机制。将耗时的命令放到后台线程运行，主线程继续处理其他工作，不阻塞 LLM 调用。

## 架构图

```
    主线程                    后台线程
+-----------------+       +-----------------+
| agent loop      |       | 任务执行中...   |
| [LLM 调用] <----|-------| 完成后入队       |
|  消费通知队列    |       +-----------------+
+-----------------+

时间线：
Agent --[spawn A]--[spawn B]--[其他工作]--
              |          |
              v          v
           [A 运行]  [B 运行]
              |          |
              +-- 通知队列 --> [结果注入]
```

## 核心概念

### 与 s12 的区别

| 特性 | s12 任务系统 | s13 后台任务 |
|------|-------------|-------------|
| 性质 | 持久化工作项 | 运行时执行槽 |
| 生命周期 | 跨对话持久 | 单次运行 |
| 存储 | `.tasks/*.json` | `.runtime-tasks/*.json` |
| 状态 | pending/completed | running/completed/timeout/error |

## NotificationQueue

优先级通知队列，支持同 key 消息折叠。

### 优先级

```
immediate (0) > high (1) > medium (2) > low (3)
```

### 折叠机制

相同 key 的消息会被新消息替换，避免上下文被重复更新淹没：

```python
queue.push("进度1", key="task_progress")  # 旧消息
queue.push("进度2", key="task_progress")  # 替换前者
```

## BackgroundManager

### 核心方法

| 方法 | 功能 |
|------|------|
| `run(command)` | 启动后台线程，立即返回 task_id |
| `check(task_id)` | 查看单个任务状态 |
| `drain_notifications()` | 消费所有完成通知 |
| `detect_stalled()` | 检测超时任务（>45s） |

### 任务状态

| 状态 | 说明 |
|------|------|
| `running` | 执行中 |
| `completed` | 正常完成 |
| `timeout` | 超时（300s） |
| `error` | 执行错误 |

### 执行流程

```
1. run(command)
   - 生成 task_id (UUID 前8位)
   - 创建 daemon 线程
   - 立即返回 task_id

2. _execute(task_id, command)
   - 运行 subprocess (300s 超时)
   - 写入 .runtime-tasks/{task_id}.log
   - 更新任务状态到 .runtime-tasks/{task_id}.json
   - 通知入队
```

## 后台任务工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `background_run` | command | 启动后台任务，立即返回 |
| `check_background` | task_id (可选) | 查看任务状态 |

## agent_loop 中的通知注入

每次 LLM 调用前，检查是否有后台任务完成：

```python
notifs = BG.drain_notifications()
if notifs:
    messages.append({
        "role": "user",
        "content": f"<background-results>\n{notif_text}\n</background-results>"
    })
```

## 持久化结构

```
.runtime-tasks/
  {task_id}.json   # 任务记录
  {task_id}.log    # 输出日志
```

### 任务记录结构

```json
{
  "id": "abc12345",
  "status": "completed",
  "command": "npm build",
  "result": "Build successful...",
  "result_preview": "Build success...",
  "started_at": 1234567890.0,
  "finished_at": 1234567920.0,
  "output_file": ".runtime-tasks/abc12345.log"
}
```

## 测试方法

```bash
python s13_background_tasks.py
```

### 交互示例

```
s13 >> 在后台运行 sleep 命令：sleep 3 && echo "done"

> background_run:
Background task abc12345 started: sleep 3 && echo "done"
(output_file=.runtime-tasks/abc12345.log)

s13 >> 列出所有后台任务

s13 >> 查看任务 abc12345 的状态

s13 >> 查看完整输出：读取文件 .runtime-tasks/abc12345.log
```

### 多任务并发

```
s13 >> 启动三个后台任务：
- sleep 2 && echo "task1"
- sleep 5 && echo "task2"
- find / -name "*.py" 2>/dev/null | head -10
```

### 对比阻塞 vs 后台

```bash
# 阻塞（会卡住等待）
s13 >> 运行：sleep 10 && echo "同步完成"

# 后台（立即返回）
s13 >> 后台运行：sleep 10 && echo "异步完成"
```

## 常量配置

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `STALL_THRESHOLD_S` | 45 | 任务超时判定（秒） |
| subprocess timeout | 300 | 最大执行时间 |

## 目录结构

```
learn_claude_code/
├── .runtime-tasks/        # 运行时任务目录
│   ├── abc12345.json
│   ├── abc12345.log
│   └── ...
├── s13_background_tasks.py
└── s13_README.md
```

## 注意事项

1. **Daemon 线程**: 后台任务使用 daemon 线程，主进程退出时自动终止
2. **UUID 碰撞**: task_id 是 UUID 前8位，极低概率碰撞
3. **输出限制**: 单个输出最大 50000 字符
4. **超时保护**: subprocess 最大运行 300 秒

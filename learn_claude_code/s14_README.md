# s14 - Cron 定时任务调度器 (Cron Scheduler)

## 概述

`s14_cron_scheduler.py` 演示了定时任务调度机制。Agent 可以使用标准 cron 表达式安排未来执行的提示，当时间到达时自动注入到对话中。

## Cron 表达式

```
5字段格式: min hour dom month dow
+-------+-------+-------+-------+-------+
| min   | hour  | dom   | month | dow   |
| 0-59  | 0-23  | 1-31  | 1-12  | 0-6   |
+-------+-------+-------+-------+-------+

特殊符号:
  *       任意值
  */N     每 N 个单位
  N-M     范围
  N,M     列表

常用示例:
  "*/5 * * * *"   每 5 分钟
  "0 9 * * 1"     周一 9:00
  "30 14 * * *"   每天 14:30
  "0 */2 * * *"   每 2 小时
```

## 架构图

```
后台线程 (每秒检查)
    │
    ├── for each task:
    │     if cron_matches(now):
    │       enqueue notification
    │       (one-shot: auto-delete)
    │       (recurring: keep, +7d expiry)
    │
    ▼
通知队列 (Queue)
    │
    ▼ (agent_loop 每次 LLM 调用前 drain)
注入为 user message
```

## 持久化模式

| 模式 | 说明 | 存储 |
|------|------|------|
| session-only | 内存列表，退出后丢失 | 内存 |
| durable | 持久化到磁盘 | `.claude/scheduled_tasks.json` |

## 触发模式

| 模式 | 说明 |
|------|------|
| recurring | 重复执行，直到删除或 7 天后自动过期 |
| one-shot | 执行一次后自动删除 |

## 定时任务工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `cron_create` | cron, prompt, recurring, durable | 创建定时任务 |
| `cron_delete` | id | 删除任务 |
| `cron_list` | - | 列出所有任务 |

## CronScheduler 核心方法

| 方法 | 功能 |
|------|------|
| `create()` | 创建定时任务 |
| `delete()` | 删除任务 |
| `list_tasks()` | 列出所有任务 |
| `drain_notifications()` | 消费通知队列 |
| `detect_missed_tasks()` | 检测错过的任务 |
| `_load_durable()` | 从磁盘加载持久化任务 |
| `_save_durable()` | 保存任务到磁盘 |

## 防重复机制

| 机制 | 说明 |
|------|------|
| CronLock | PID 文件锁，防止多会话重复触发 |
| 每分钟检查 | `_last_check_minute` 避免同分钟重复触发 |
| Jitter | recurring 任务在 :00/:30 时添加 1-4 分钟偏移 |

## CronLock 锁机制

```python
class CronLock:
    def acquire(self) -> bool:
        # 检查锁文件是否存在
        # 存在则验证 PID 是否存活 (os.kill(pid, 0))
        # 进程存活则返回 False（锁被占用）
        # 进程已死则移除旧锁，创建新锁
        
    def release(self):
        # 只删除属于当前进程的锁文件
```

## 错过任务检测

```python
def detect_missed_tasks(self) -> list[dict]:
    # 检查上次触发到现在的时段
    # 如果包含 cron 匹配时间点，标记为 missed
    # 最多回溯 24 小时
```

## 持久化结构

```json
// .claude/scheduled_tasks.json
[
  {
    "id": "abc12345",
    "cron": "0 9 * * *",
    "prompt": "每日检查",
    "recurring": true,
    "durable": true,
    "createdAt": 1234567890.0,
    "last_fired": 1234567890.0,
    "jitter_offset": 2
  }
]
```

## 测试方法

```bash
python s14_cron_scheduler.py
```

### 交互命令

```
# 列出定时任务
s14 >> /cron

# 测试通知
s14 >> /test

# 退出
s14 >> q
```

### 创建任务示例

```
# 持久化任务（退出后保留）
s14 >> 创建定时任务：cron="0 9 * * *" prompt="每日检查" durable=true

# Session-only（退出后丢失）
s14 >> 创建定时任务：cron="* * * * *" prompt="临时任务"

# 一次性任务
s14 >> 创建定时任务：cron="*/2 * * * *" prompt="两分钟后提醒" recurring=false
```

### 验证持久化

```bash
# 重启后查看任务文件
cat .claude/scheduled_tasks.json

# 查看锁文件
cat .claude/cron.lock
```

### 测试场景

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| Session-only 丢失 | 创建任务，退出，重启 | 任务不存在 |
| Durable 保留 | 创建 durable=true，退出，重启 | 任务存在 |
| One-shot 自动删除 | 创建 recurring=false，等待触发 | 触发后自动删除 |
| 多会话冲突 | 两个终端同时运行 | 第二个进程检测到锁，不触发 |

## 与 s12/s13 对比

| 特性 | s12 任务系统 | s13 后台任务 | s14 定时调度 |
|------|-------------|-------------|-------------|
| 触发方式 | 手动创建/完成 | 后台异步执行 | 时间驱动 |
| 生命周期 | 跨会话持久 | 单次运行 | 定时循环 |
| 持久化 | 磁盘 | 磁盘 | 可选磁盘 |

## 目录结构

```
learn_claude_code/
├── .claude/
│   ├── scheduled_tasks.json   # 持久化任务
│   └── cron.lock              # 锁文件
├── s14_cron_scheduler.py
└── s14_README.md
```

## 常量配置

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `AUTO_EXPIRY_DAYS` | 7 | recurring 任务自动过期天数 |
| `JITTER_MINUTES` | [0, 30] | 添加 jitter 的分钟边界 |
| `JITTER_OFFSET_MAX` | 4 | jitter 偏移最大值（分钟） |

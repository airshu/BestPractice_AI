# Memory System - s09_memory_system.py

一个教学级别的记忆系统，展示如何让 AI Agent 跨会话持久化记忆信息。

## 核心设计理念

> "Memory only stores cross-session information that is still worth recalling later and is not easy to re-derive from the current repo."

**记忆** 用于存储跨会话的持久化信息，而非所有上下文数据。

## 核心原则

### ✅ 应该存储

| 类型 | 说明 | 示例 |
|------|------|------|
| `user` | 用户偏好 | "我更喜欢用 tabs" |
| `feedback` | 用户纠正 | "不要那样做，原因是..." |
| `project` | 非显而易见的项目事实 | 合规规则、遗留代码原因 |
| `reference` | 外部资源指针 | 票据系统URL、文档链接 |

### ❌ 不应该存储

- 代码结构（可从代码库重新读取）
- 临时任务状态（当前分支、PR编号、TODO列表）
- 敏感信息（API密钥、密码）

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Session                          │
│                                                          │
│  启动 ──► MemoryManager.load_all() ──► 注入 System Prompt │
│                                                          │
│  运行 ──► save_memory 工具 ──► 写入 .memory/*.md          │
│                   │                                       │
│                   ▼                                       │
│          DreamConsolidator 整理                          │
└─────────────────────────────────────────────────────────┘
```

## 存储结构

```
.memory/
  MEMORY.md              # 索引文件（按类型分组，最多200行）
  prefer_tabs.md         # 记忆文件（frontmatter 格式）
  pep8_compliance.md
  review_style.md
```

### 文件格式

```markdown
---
name: prefer_tabs
description: User prefers tabs over spaces
type: user
---
我更喜欢用 tabs 来缩进代码，而不是 spaces
```

## save_memory 工具

```python
{
  "name": "prefer_tabs",           # 短标识符
  "description": "One-line summary", # 一行摘要
  "type": "user|feedback|project|reference",  # 记忆类型
  "content": "Full content..."     # 完整内容（支持多行）
}
```

## 使用方法

### 1. 启动

```bash
cd learn_claude_code
python s09_memory_system.py

# 输出
[No existing memories. The agent can create them with save_memory.]
s09 >>
```

### 2. 交互命令

| 命令 | 功能 |
|------|------|
| `/memories` | 列出当前所有记忆 |
| `q` / `exit` | 退出 |

### 3. 自动加载

启动时会自动：
1. 扫描 `.memory/` 目录
2. 加载所有 `.md` 文件（除 MEMORY.md）
3. 解析 frontmatter
4. 注入到 System Prompt

## 测试场景

### 场景1: 基本记忆保存

```bash
s09 >> 我更喜欢用 tabs 来缩进代码
> save_memory: Saved memory 'indent_preference' [.memory/indent_preference.md]
```

### 场景2: 项目规则记忆

```bash
s09 >> 我们的项目必须遵循PEP8规范
> save_memory: Saved memory 'pep8_compliance' [.memory/pep8_compliance.md]
```

### 场景3: 跨会话持久化

```bash
# 会话1: 保存记忆
$ python s09_memory_system.py
s09 >> 我的代码风格偏好是使用 PEP8 规范
> save_memory: Saved memory 'pep8_compliance' [.memory/pep8_compliance.md]
s09 >> q

# 会话2: 启动（记忆自动加载）
$ python s09_memory_system.py
[Memory loaded: 1 memories from .memory/]
[1 memories loaded into context]
s09 >> 我的代码风格偏好是什么？
> 模型基于记忆回答：PEP8 规范
```

### 场景4: 查看记忆列表

```bash
s09 >> /memories
  [user] indent_preference: User prefers tabs over spaces
  [project] pep8_compliance: Project follows PEP8 standard
```

## Dream Consolidation（可选功能）

自动整理记忆，防止记忆库变得嘈杂。

### 7 个门控条件

| 门控 | 条件 | 阈值 |
|------|------|------|
| 1 | consolidation 已启用 | - |
| 2 | memory 目录存在 | 有文件 |
| 3 | 非 plan 模式 | - |
| 4 | 冷却期 | 24小时 |
| 5 | 扫描节流 | 10分钟 |
| 6 | 会话数量 | ≥5 |
| 7 | 锁文件 | 无活跃锁 |

### 4 阶段整理

```
Phase 1: Orient     - 扫描索引结构
Phase 2: Gather     - 读取完整内容
Phase 3: Consolidate - 合并/去重
Phase 4: Prune      - 强制200行限制
```

### PID 锁机制

防止多进程同时整理：
- 活跃进程锁有效
- 超过1小时的锁视为过期
- 进程死亡后自动释放

## 与其他模块的关系

| 模块 | 关注点 |
|------|--------|
| `s06_context_compact.py` | 当前会话内的上下文压缩 |
| `s09_memory_system.py` | **跨会话的持久化记忆** |

## 扩展建议

1. **记忆搜索**: 添加语义搜索能力
2. **记忆版本**: 记录记忆修改历史
3. **记忆优先级**: 区分重要和次要记忆
4. **自动遗忘**: 设置记忆过期时间
5. **记忆标签**: 支持多标签分类

# System Prompt Construction - s10_system_prompt.py

一个教学级别的 System Prompt 构建系统，展示如何将提示词组装为模块化管道。

## 核心设计理念

> "Prompt construction is a pipeline with boundaries, not one big string"

**System Prompt** 应由独立模块组装，而非硬编码大字符串。这样更易理解、测试和扩展。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│              SystemPromptBuilder.build()                │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. Core Instructions     │  基础角色定义          │  │
│  │ 2. Tool Listings         │  可用工具列表          │  │
│  │ 3. Skill Metadata        │  技能元数据            │  │
│  │ 4. Memory Section        │  持久记忆              │  │
│  │ 5. CLAUDE.md Chain       │  项目指令链            │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  === DYNAMIC_BOUNDARY ===     │  静态/动态分界线     │
├─────────────────────────────────────────────────────────┤
│  6. Dynamic Context        │  动态上下文（每轮变化）  │
└─────────────────────────────────────────────────────────┘
```

## 6 层组装管道

| 层级 | 方法 | 内容 | 变化频率 |
|------|------|------|----------|
| 1 | `_build_core()` | 核心角色定义、工作目录 | 静态 |
| 2 | `_build_tool_listing()` | 工具名称和参数 | 静态 |
| 3 | `_build_skill_listing()` | skills/SKILL.md 中的技能 | 静态 |
| 4 | `_build_memory_section()` | .memory/*.md 中的记忆 | 中频 |
| 5 | `_build_claude_md()` | 3级 CLAUDE.md 指令 | 中频 |
| 6 | `_build_dynamic_context()` | 日期、平台等 | **每轮变化** |

## CLAUDE.md 链

按优先级加载多个 CLAUDE.md 文件：

```
优先级顺序:
1. ~/.claude/CLAUDE.md         → 用户全局指令
2. <project>/CLAUDE.md        → 项目根目录指令
3. <subdir>/CLAUDE.md         → 子目录指令
```

所有存在的 CLAUDE.md 都会被加载，内容按优先级依次拼接。

## DYNAMIC_BOUNDARY

```python
DYNAMIC_BOUNDARY = "=== DYNAMIC_BOUNDARY ==="
```

**作用**：
- 静态部分（1-5层）可跨轮次缓存，节省 token
- 动态部分（6层）每轮更新
- 实际 Claude Code 在边界处截断缓存，只追加动态内容

## System Reminder

用于**每轮动态注入**的临时提醒：

```python
build_system_reminder(extra="临时提醒内容")
# → {"role": "user", "content": "<system-reminder>...</system-reminder>"}
```

**设计原则**：短生命周期内容不应混入长生命周期指令。

## 使用方法

### 1. 启动

```bash
cd learn_claude_code
python s10_system_prompt.py

# 输出
[System prompt assembled: 2048 chars, ~5 sections]
s10 >>
```

### 2. 交互命令

| 命令 | 功能 |
|------|------|
| `/prompt` | 查看完整组装的 System Prompt |
| `/sections` | 查看 Prompt 分段结构 |
| `q` / `exit` | 退出 |

### 3. 查看完整 Prompt

```
s10 >> /prompt
--- System Prompt ---
You are a coding agent operating in /path/to/workdir.
...

# Available tools
- bash(command): Run a shell command.
- read_file(path, limit): Read file contents.
...

# Memories (persistent)
[user] indent_preference: User prefers tabs
...

=== DYNAMIC_BOUNDARY ===
# Dynamic context
Current date: 2026-04-15
...
--- End ---
```

### 4. 查看分段结构

```
s10 >> /sections
  # You are a coding agent...
  # Available tools
  # Available skills
  # Memories (persistent)
  # CLAUDE.md instructions
  === DYNAMIC_BOUNDARY ===
  # Dynamic context
```

## 测试场景

### 场景1: 查看默认 Prompt

```bash
python s10_system_prompt.py
/prompt
```

### 场景2: 创建用户全局指令

```bash
# 创建用户全局 CLAUDE.md
mkdir -p ~/.claude
echo "User prefers concise responses" > ~/.claude/CLAUDE.md

# 重新运行
python s10_system_prompt.py
/prompt

# 查看输出
# CLAUDE.md instructions
## From user global (~/.claude/CLAUDE.md)
User prefers concise responses
```

### 场景3: 创建项目级指令

```bash
# 项目根目录
echo "This project follows PEP8 style guide" > CLAUDE.md

# 子目录
echo "Tests should use pytest framework" > learn_claude_code/CLAUDE.md

python s10_system_prompt.py
/prompt
```

### 场景4: 验证动态部分每轮变化

```bash
python s10_system_prompt.py

# 注意观察 Dynamic context 部分
s10 >> /sections
  ...
  === DYNAMIC_BOUNDARY ===
  # Dynamic context
  Current date: 2026-04-15

# 第二天运行，日期会自动更新
```

## 静态 vs 动态对比

| 类型 | 内容 | 优化策略 |
|------|------|----------|
| **静态** | Core、Tools、Skills、Memory、CLAUDE.md | 跨轮次缓存 |
| **动态** | 日期、时间、平台 | 每轮更新 |

**实际效果**：Claude Code 通过在 `DYNAMIC_BOUNDARY` 处截断缓存，静态部分只加载一次，大幅节省 token。

## 与其他模块的关系

| 模块 | 关注点 |
|------|--------|
| `s05_skill_loading.py` | 技能加载系统 |
| `s09_memory_system.py` | 持久化记忆 |
| `s10_system_prompt.py` | **提示词模块化组装** |

## 扩展建议

1. **条件化层**: 根据模式（plan/auto）选择性加载层
2. **优先级控制**: 支持配置各层的加载优先级
3. **模板支持**: 层内容支持变量替换
4. **Prompt 版本**: 支持版本化 Prompt 管理
5. **调试工具**: 添加 Prompt 性能分析

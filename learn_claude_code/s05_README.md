# s05 - 技能加载系统 (Skill Loading)

## 概述

`s05_skill_loading.py` 演示了两层技能模型：
1. 在 system prompt 中放置廉价的技能目录
2. 只有当模型请求时才加载完整技能体

这保持了 prompt 精简，同时让模型可以访问可复用的任务特定指导。

## 核心概念

| 概念 | 说明 |
|------|------|
| SkillManifest | 技能清单：name、description、path |
| SkillDocument | 技能文档：manifest + body |
| SkillRegistry | 技能注册表：加载和管理技能 |

## 两层技能模型

```
System Prompt（精简）:
┌─────────────────────────────────────┐
│ Skills available:                   │
│ - python: Python 编程规范            │
│ - bash: Shell 脚本指南              │
│ - git: Git 工作流程                 │
└─────────────────────────────────────┘
      │
      │ 模型调用 load_skill("python")
      ▼
Full Skill Body（按需加载）:
┌─────────────────────────────────────┐
│ <skill name="python">              │
│ ## Python 编码规范                  │
│ 1. 遵循 PEP 8                      │
│ 2. 使用类型提示                    │
│ 3. ...                             │
│ </skill>                           │
└─────────────────────────────────────┘
```

## 技能文件结构

```
skills/
  python/
    SKILL.md
  bash/
    SKILL.md
  git/
    SKILL.md
```

### SKILL.md 格式

```markdown
---
name: python
description: Python 编程最佳实践指南
---

## Python 编码规范

1. 遵循 PEP 8
2. 使用类型提示
3. 写 docstring
4. ...
```

## SkillRegistry 核心方法

| 方法 | 功能 |
|------|------|
| `_load_all()` | 扫描 skills/**/SKILL.md，加载所有技能 |
| `_parse_frontmatter()` | 解析 YAML frontmatter |
| `describe_available()` | 生成技能目录文本 |
| `load_full_text()` | 加载完整技能体 |

## 工具接口

| 工具 | 参数 | 说明 |
|------|------|------|
| `load_skill` | name | 加载完整技能到上下文 |

### load_skill 输出格式

```xml
<skill name="python">
## Python 编码规范

1. 遵循 PEP 8
2. 使用类型提示
...
</skill>
```

## System Prompt 模板

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill when a task needs specialized instructions before you act.
Skills available:
{SKILL_REGISTRY.describe_available()}
"""
```

## 加载时机

| 方式 | 说明 |
|------|------|
| 模型主动调用 | 模型判断需要时调用 load_skill |
| 按需加载 | 只在需要时加载完整内容，节省 token |

## 与 s04 子 Agent 的区别

| 特性 | s04 Subagent | s05 Skill |
|------|-------------|----------|
| 目的 | 隔离执行上下文 | 提供领域知识 |
| 返回 | 摘要 | 技能文本 |
| 上下文 | 新建独立消息 | 追加到当前上下文 |
| 粒度 | 任务级 | 指南级 |

## 测试方法

```bash
python s05_skill_loading.py
```

### 前提条件

创建技能目录和技能文件：

```bash
mkdir -p skills/python
cat > skills/python/SKILL.md << 'EOF'
---
name: python
description: Python 编程最佳实践
---

## Python 编码规范

1. 遵循 PEP 8
2. 使用类型提示
3. 写 docstring
EOF
```

### 交互示例

```
s05 >> 列出可用技能
Skills available:
- python: Python 编程最佳实践

s05 >> 加载 Python 技能

> load_skill:
<skill name="python">
## Python 编码规范

1. 遵循 PEP 8
...
</skill>

s05 >> 写一个符合规范的 Python 函数

s05 >> q
```

### 测试按需加载

1. 不加载技能时，让模型直接写代码
2. 加载技能后，让模型写代码
3. 对比两次输出的质量

## 目录结构

```
learn_claude_code/
├── skills/                   # 技能目录
│   ├── python/
│   │   └── SKILL.md
│   ├── bash/
│   │   └── SKILL.md
│   └── git/
│       └── SKILL.md
├── s05_skill_loading.py
└── s05_README.md
```

## 优势

1. **节省 Token**: system prompt 保持精简
2. **按需加载**: 只加载需要的技能
3. **可扩展**: 易于添加新技能
4. **可维护**: 技能内容独立管理

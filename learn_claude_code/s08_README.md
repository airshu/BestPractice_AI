# Hook System - s08_hook_system.py

一个教学级别的钩子系统，展示如何在不修改主循环的情况下扩展 Agent 行为。

## 核心设计理念

> "Extend the agent without touching the loop"

**Hook** 是在主循环中注入扩展行为的"挂钩点"，无需修改核心代码即可添加新功能。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Loop                            │
│                                                          │
│  SessionStart ──┐                                        │
│                 ▼                                        │
│  ┌──────────────────────────────┐                      │
│  │         PreToolUse            │ ◄── 可阻止/修改输入   │
│  └──────────────────────────────┘                      │
│                 │                                        │
│                 ▼                                        │
│  ┌──────────────────────────────┐                      │
│  │        Execute Tool          │                       │
│  └──────────────────────────────┘                      │
│                 │                                        │
│                 ▼                                        │
│  ┌──────────────────────────────┐                      │
│  │         PostToolUse          │ ◄── 可注入额外消息    │
│  └──────────────────────────────┘                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 三种 Hook 事件

| 事件 | 触发时机 | 常见用途 |
|------|----------|----------|
| `SessionStart` | 会话启动时 | 初始化、日志记录、环境检查 |
| `PreToolUse` | 工具执行前 | 输入验证、权限检查、安全扫描 |
| `PostToolUse` | 工具执行后 | 结果处理、日志记录、后置处理 |

## 退出码协议

Hook 脚本通过退出码返回控制指令：

| 退出码 | 行为 | 说明 |
|--------|------|------|
| `0` | 继续执行 | 正常通过，可选输出 JSON |
| `1` | 阻止操作 | 阻止工具执行，返回错误信息 |
| `2` | 注入消息 | 通过 stderr 注入消息到对话 |

## 配置文件格式

创建 `.hooks.json` 配置文件：

```json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "*", "command": "echo '=== Session Started ==='"}
    ],
    "PreToolUse": [
      {"matcher": "bash", "command": "./validate_bash.sh"},
      {"matcher": "write_file", "command": "./check_path.sh"}
    ],
    "PostToolUse": [
      {"matcher": "read_file", "command": "./log_read.sh"}
    ]
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `matcher` | string | 工具名过滤 (`*` 表示所有工具) |
| `command` | string | 执行的命令 (支持 shell) |

## 环境变量

Hook 运行时可访问以下环境变量：

| 变量名 | 内容 |
|--------|------|
| `HOOK_EVENT` | 当前事件名称 (`SessionStart`/`PreToolUse`/`PostToolUse`) |
| `HOOK_TOOL_NAME` | 被调用的工具名 |
| `HOOK_TOOL_INPUT` | 工具输入参数 (JSON 格式，限制 10000 字符) |
| `HOOK_TOOL_OUTPUT` | 工具输出结果 (仅 PostToolUse) |

## 信任机制

Hook 只在工作区被信任时运行，防止恶意 hook：

```bash
# 创建信任标记
mkdir -p .claude
touch .claude/.claude_trusted
```

| 条件 | 是否执行 hooks |
|------|----------------|
| `.claude/.claude_trusted` 存在 | ✅ 执行 |
| `.claude/.claude_trusted` 不存在 | ❌ 跳过 |
| SDK 模式 (`sdk_mode=True`) | ✅ 隐式信任 |

## Hook 输出格式 (可选)

Hook 可输出 JSON 到 stdout 以实现更精细的控制：

```json
{
  "updatedInput": {...},      // 修改工具输入 (PreToolUse)
  "additionalContext": "...", // 注入额外上下文
  "permission_override": "allow" // 覆盖权限决策
}
```

## 使用方法

### 1. 启动

```bash
cd learn_claude_code
python s08_hook_system.py
```

### 2. 观察 Hook 执行

```bash
# 创建信任标记 (首次)
mkdir -p .claude && touch .claude/.claude_trusted

# 重新运行
python s08_hook_system.py

# 预期输出：
[Hooks loaded from .hooks.json]
[hook:SessionStart] === Session Started ===
s08 >> 读取文件
> read_file: ...
[hook:PostToolUse] PostToolUse: finished reading
```

## 测试场景

### 场景1: 测试消息注入 (exit 2)

```bash
# 创建 hook 脚本
cat > inject_msg.sh << 'EOF'
#!/bin/bash
echo "Warning: Large file detected" >&2
exit 2
EOF
chmod +x inject_msg.sh

# 更新 .hooks.json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "read_file", "command": "./inject_msg.sh"}
    ]
  }
}
```

**效果**: 读取大文件时会注入警告消息

### 场景2: 测试阻止功能 (exit 1)

```bash
# 创建阻止脚本
cat > block_write.sh << 'EOF'
#!/bin/bash
echo "Write operations are blocked by policy"
exit 1
EOF
chmod +x block_write.sh

# 更新 .hooks.json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "write_file", "command": "./block_write.sh"}
    ]
  }
}
```

**效果**: 所有 write_file 调用都会被阻止

### 场景3: 输入验证/修改 (JSON 输出)

```bash
# 创建输入验证脚本
cat > validate_path.sh << 'EOF'
#!/bin/bash
if echo "$HOOK_TOOL_INPUT" | grep -q "\.\./"; then
  echo "Security: Path traversal detected" >&2
  exit 1
fi
exit 0
EOF
chmod +x validate_path.sh
```

## 与其他模块的关系

| 模块 | 关注点 |
|------|--------|
| `s06_context_compact.py` | 上下文压缩 |
| `s07_permission_system.py` | 权限控制 |
| `s08_hook_system.py` | 行为扩展 |

## 扩展建议

1. **SessionEnd Hook**: 添加会话结束时的清理/报告
2. **PreMessage Hook**: 在发送消息前进行审查
3. **规则引擎**: 支持更复杂的匹配条件
4. **异步执行**: 支持长时间运行的 hook
5. **Hook 链**: 支持 hook 之间的数据传递

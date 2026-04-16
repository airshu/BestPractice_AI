# Permission System - s07_permission_system.py

一个教学级别的权限控制系统，展示如何在 AI Agent 执行工具前进行安全检查和权限管理。

## 核心设计理念

> "安全是一个管道，而不是布尔值"

每个工具调用都经过**四层权限管道**检查，确保只有符合策略的操作才能执行。

## 架构概览

```
工具调用 → ① Bash验证 → ② 拒绝规则 → ③ 模式检查 → ④ 允许规则 → ⑤ 询问用户
```

## 三种权限模式

| 模式 | 描述 | 写入操作 |
|------|------|----------|
| `default` | 严格模式 | 需用户确认 |
| `plan` | 只读模式 | 拒绝所有写入 |
| `auto` | 自动模式 | 只读自动放行 |

## Bash 安全验证

内置正则规则检测危险命令：

| 规则名 | 模式 | 风险等级 |
|--------|------|----------|
| `shell_metachar` | `[;&|\`$]` | 询问用户 |
| `sudo` | `\bsudo\b` | **直接拒绝** |
| `rm_rf` | `rm\s+(-[a-zA-Z]*)?r` | **直接拒绝** |
| `cmd_substitution` | `\$\(` | 询问用户 |
| `ifs_injection` | `\bIFS\s*=` | 询问用户 |

## 默认权限规则

```python
DEFAULT_RULES = [
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},  # 硬编码拒绝
    {"tool": "bash", "content": "sudo *", "behavior": "deny"},      # 拒绝所有sudo
    {"tool": "read_file", "path": "*", "behavior": "allow"},        # 读文件全部放行
]
```

## 使用方法

### 启动

```bash
cd learn_claude_code
python s07_permission_system.py
```

### 交互命令

| 命令 | 功能 |
|------|------|
| `y` | 允许当前操作一次 |
| `n` | 拒绝当前操作 |
| `always` | 添加永久允许规则 |
| `/mode <mode>` | 切换权限模式 |
| `/rules` | 查看当前规则列表 |
| `q` / `exit` | 退出 |

### 模式切换示例

```
s07 >> /mode plan     # 切换到只读模式
s07 >> /mode auto     # 切换到自动模式
s07 >> /mode default  # 切换到默认模式
```

## 测试场景

### 场景1: 测试 plan 模式拒绝写入

```bash
$ python s07_permission_system.py
Mode (default): plan

s07 >> 帮我创建一个测试文件
[DENIED] Plan mode: write operations are blocked
```

### 场景2: 测试 default 模式询问

```bash
$ python s07_permission_system.py
Mode (default): default

s07 >> 创建一个测试文件
[Permission] write_file: {"path": "test.txt", "content": "..."}
Allow? (y/n/always): y
> write_file: Wrote 100 bytes
```

### 场景3: 测试危险命令拒绝

```bash
s07 >> 执行 rm -rf / 删除所有文件
[DENIED] Bash validator: rm -rf / pattern detected
```

## 文件结构

```
learn_claude_code/
├── s07_permission_system.py    # 主程序
├── .claude/                    # 信任标记目录(可选)
│   └── .claude_trusted         # 信任标记文件(可选)
```

## 信任工作区

如果工作区标记为信任，某些安全限制可能被放宽：

```bash
mkdir -p .claude
touch .claude/.claude_trusted
```

## 扩展建议

1. **添加更多危险命令检测**: 如 `mkfs`, `dd`, `chmod 777`
2. **路径白名单**: 只允许在特定目录执行写操作
3. **命令频率限制**: 防止短时间内大量操作
4. **审计日志**: 记录所有权限决策
5. **规则持久化**: 将规则保存到配置文件

## 与其他模块的关系

- `s06_context_compact.py`: 上下文压缩（关注点：对话长度）
- `s07_permission_system.py`: 权限控制（关注点：操作安全）

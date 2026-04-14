# Lesson 11: 部署前安全防护 (Pre-Deployment Safeguards)

## 📚 核心概念

在将 LLM 应用部署到生产环境前，需要识别并消除**关键风险点**。这一课讲解生产工程 3 大必备防护。

---

## 🔴 三大部署风险

### Risk 1️⃣: API 超时风险 ⏱️

**问题描述**
```python
# ❌ 危险代码
resp = client.responses.create(model=model, input=prompt)  # 无超时控制
```

- API 可能因网络问题、服务过载而响应缓慢
- 没有超时设置 → 进程可能无限期等待
- 若处理 1000 条数据，1 条卡住 → 整个批处理失败

**影响**
- ⏰ CPU 占用，资源浪费
- 📊 监控告警，人工介入
- 💰 超期计费（某些云服务）

**解决方案：超时装饰器**
```python
@timeout_decorator(timeout_sec=30.0)
def _call_with_timeout():
    resp = client.responses.create(model=model, input=prompt)
    return resp.output_text.strip()
```
- 设定合理的超时时间（30 秒）
- 超时自动抛异常，进程继续
- 结果分类记录为 `api_timeout` 错误

---

### Risk 2️⃣: 写入损坏风险 💾

**问题描述**
```python
# ❌ 危险代码
with open("results.json", "w") as f:
    json.dump(results, f)  # 直接写入
# 中途断电 → results.json 损坏，数据全丢
```

**影响**
- 🔥 之前所有成功结果丢失
- 📉 需要重新处理全部数据
- 💸 重复调用 API，浪费配额

**解决方案：原子性写入**
```python
def safe_write_json(file_path, data):
    # 1. 写入临时文件
    temp_fd, temp_path = tempfile.mkstemp(suffix=".json")
    
    # 2. 验证数据完整性
    with open(temp_path, 'r') as f:
        verify = json.load(f)  # 确保数据可读
    
    # 3. 备份旧文件
    if os.path.exists(file_path):
        os.rename(file_path, file_path + ".backup")
    
    # 4. 原子重命名（POSIX 保证原子性）
    os.rename(temp_path, file_path)
```

**关键步骤**
| 步骤 | 作用 | 风险 |
|------|------|------|
| 临时文件 | 隔离写入 | - |
| 验证完整性 | 检查数据有效 | 发现坏数据及时中止 |
| 备份旧文件 | 保留历史 | 可恢复 |
| 原子重命名 | 无中间态 | 中断时 temp 或 old 存在，但 target 不损坏 |

---

### Risk 3️⃣: 故障恢复风险 🔄

**问题描述**
```python
# ❌ 没有检查点
for item in items:  # 处理 1000 条
    result = process(item)
    results.append(result)
# 第 800 条时 API 服务崩溃
# → 需要重新处理前 800 条（浪费时间和配额）
```

**影响**
- 🔁 无法恢复，只能从头开始
- ⏲️ 处理时间翻倍
- 💰 API 成本翻倍

**解决方案：定期检查点（Checkpoint）**
```python
checkpoint_interval = 5  # 每 5 条保存一次

for i, item in enumerate(items_to_process, 1):
    out = process_one(client, model, item)
    
    if i % checkpoint_interval == 0:
        checkpoint_num += 1
        save_checkpoint(results, failed, checkpoint_num)
        # 保存 checkpoint_001.json, checkpoint_002.json, ...
```

**恢复流程**
```bash
# 第 1 次运行：处理全部，在第 800 条失败
$ python CustomerService.py --overwrite
# 结果：checkpoint_160.json（保存了前 800 条）

# 修复 API 问题后，继续从 cmt_801 开始
$ python CustomerService.py --start-id cmt_801 --sleep 0.1
# 结果：加载 checkpoint 的结果，只处理新项
```

---

## ✅ Lesson 11 改动清单

### 1. 添加超时保护

**文件**: `CustomerService.py`

**新增函数**
```python
def timeout_decorator(timeout_seconds: float):
    """超时装饰器：确保函数在指定时间内完成"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.warning(f"[Timeout Warning] took {elapsed:.2f}s")
            return result
        return wrapper
    return decorator
```

**修改 `call_model()` 函数**
```python
def call_model(client, model, prompt, timeout_sec=30.0):
    @timeout_decorator(timeout_sec)
    def _call_with_timeout():
        resp = client.responses.create(model=model, input=prompt)
        return resp.output_text.strip()
    
    try:
        return _call_with_timeout()
    except TimeoutError:
        logger.error(f"API call exceeded timeout")
        raise
```

**修改 `process_one()` 函数**
- 捕获 `TimeoutError` → 记录为 `api_timeout` 错误
- 修复调用也加超时保护
- 修复超时时记录 `repair_timeout` 错误

### 2. 原子性写入

**新增函数**
```python
def safe_write_json(file_path, data, description):
    """原子性写入 JSON 文件（无中间损坏风险）"""
    temp_fd, temp_path = tempfile.mkstemp(suffix=".json")
    
    try:
        # 写入并验证
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 验证完整性
        with open(temp_path, 'r') as f:
            verify = json.load(f)
        
        # 备份旧文件
        if os.path.exists(file_path):
            os.rename(file_path, file_path + ".backup_...")
        
        # 原子重命名
        os.rename(temp_path, file_path)
        logger.info(f"✓ Safely wrote {len(data)} items to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Safe write failed: {str(e)}")
        return False
```

**修改 `main()` 的输出部分**
```python
# 修改前
with open("results.json", "w") as f:
    json.dump(results, f)

# 修改后
success_write = safe_write_json("results.json", results, "results")
failed_write = safe_write_json("failed.json", failed, "failures")

if not (success_write and failed_write):
    logger.error("Output files failed to write")
    return  # 失败时停止，不继续
```

### 3. 定期检查点

**新增函数**
```python
def save_checkpoint(results, failed, checkpoint_num):
    """保存中间结果检查点"""
    checkpoint_file = f"checkpoint_{checkpoint_num:03d}.json"
    checkpoint_data = {
        "timestamp": datetime.now().isoformat(),
        "checkpoint_num": checkpoint_num,
        "results_count": len(results),
        "failed_count": len(failed),
    }
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    logger.info(f"Checkpoint {checkpoint_num} saved")
```

**修改 `main()` 的处理循环**
```python
checkpoint_interval = 5
checkpoint_num = 0

for i, item in enumerate(items_to_process, 1):
    out = process_one(client, model, item)
    # ... 处理结果 ...
    
    if i % checkpoint_interval == 0:
        checkpoint_num += 1
        save_checkpoint(results, failed, checkpoint_num)
```

---

## 🧪 测试部署防护

### 测试场景 1: 正常批处理

```bash
cd /Users/xpeng/AI/github/BestPractice_AI/prompt_example
python CustomerService.py --overwrite --sleep 0.1

# 预期结果
# ✓ results.json 原子性写入成功
# ✓ failed.json 原子性写入成功
# ✓ checkpoint_*.json 每 5 条保存一次
```

### 测试场景 2: 恢复处理

```bash
# 手动中断第一次运行（Ctrl+C）
python CustomerService.py --overwrite --sleep 0.3

# 从中断点继续（假设在 cmt_008 处停止）
python CustomerService.py --start-id cmt_009 --sleep 0.1

# 预期结果
# ✓ 加载 checkpoint 信息
# ✓ 只处理 cmt_009 之后的项
# ✓ 结果自动合并无重复
```

### 测试场景 3: 验证原子性写入

```bash
# 查看备份文件
ls -lh results.json*
# results.json (最新)
# results.json.backup_20260414_... (上一版本)

# 验证文件可读
python -c "import json; print(len(json.load(open('results.json'))))"
# 输出：数据项数（健康状态）
```

---

## 📊 Lesson 11 完成检查表

- [ ] 添加 `timeout_decorator()` 函数，超时时间设为 30 秒
- [ ] 修改 `call_model()` 使用超时保护
- [ ] 修改 `process_one()` 捕获 `TimeoutError` 和 `api_timeout` 错误
- [ ] 添加 `safe_write_json()` 函数，实现原子性写入
- [ ] 修改 `main()` 使用安全写入函数
- [ ] 添加 `save_checkpoint()` 函数
- [ ] 修改处理循环，每 5 条保存一个检查点
- [ ] 验证代码语法：`python -m py_compile CustomerService.py` ✓
- [ ] 运行 `python CustomerService.py --overwrite` 完整批处理
- [ ] 验证 `results.json` 和 `failed.json` 文件完整
- [ ] （可选）验证 `checkpoint_*.json` 文件创建

---

## 🎯 核心要点总结

| 风险 | 原因 | 防护 | 效果 |
|------|------|------|------|
| ⏱️ API 超时 | 网络/服务延迟 | `timeout_decorator` | 超时自动中止，避免无限等待 |
| 💾 写入损坏 | 中途断电/断网 | `safe_write_json` + 原子重命名 | 旧数据不损坏，可回滚 |
| 🔄 无法恢复 | 中途失败 | `save_checkpoint` 定期保存 | 失败后可从检查点继续 |

---

## 下一步（Lesson 12）

**后发大监控 (Post-Launch Monitoring)**
- 日常样本审核机制
- 指标漂移检测
- 周报数据分析


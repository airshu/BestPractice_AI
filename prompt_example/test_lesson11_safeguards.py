#!/usr/bin/env python3
"""
Lesson 11 安全防护演示脚本
演示：超时保护、原子性写入、检查点恢复
"""

import json
import time
import tempfile
import os
from datetime import datetime

def demo_timeout_protection():
    """演示超时保护的效果"""
    print("\n" + "="*60)
    print("演示 1️⃣: 超时保护 (Timeout Protection)")
    print("="*60)
    
    print("""
    场景：API 响应缓慢，无超时时进程卡住
    
    ❌ 无超时保护:
        start_time = time.time()
        response = client.api_call()  # 可能卡住 10+ 分钟
        elapsed = time.time() - start_time
        print(f"等待了 {elapsed:.0f} 秒")  # 可能是 600+ 秒
    
    ✅ 有超时保护:
        @timeout_decorator(timeout_sec=30.0)
        def api_call():
            return client.api_call()
        
        try:
            response = api_call()  # 最多等待 30 秒
        except TimeoutError:
            logger.error("API 超时，记录为失败，继续处理下一条")
    """)
    
    # 模拟超时保护的效果
    print("\n模拟：处理 20 条数据，第 8 条 API 超时")
    simulated_results = []
    for i in range(1, 21):
        if i == 8:
            simulated_results.append({
                "id": f"cmt_{i:03d}",
                "status": "timeout",
                "error": "api_timeout",
                "time_spent": "30.0s (hit timeout limit)"
            })
            print(f"  [{i:2d}] ❌ API 超时（自动中止，未无限等待）")
        else:
            simulated_results.append({
                "id": f"cmt_{i:03d}",
                "status": "success",
                "confidence": 0.92
            })
            print(f"  [{i:2d}] ✅ 成功")
    
    print(f"\n结果：{len([x for x in simulated_results if x['status'] == 'success'])}/20 成功")
    print("     第 8 条超时，但进程继续处理第 9-20 条 ✓")

def demo_atomic_write():
    """演示原子性写入的安全性"""
    print("\n" + "="*60)
    print("演示 2️⃣: 原子性写入 (Atomic Write)")
    print("="*60)
    
    print("""
    场景：写入过程中突然断电
    
    ❌ 直接写入（不安全）:
        with open("results.json", "w") as f:
            json.dump(large_data, f)
        # 中途断电 → results.json 损坏，全部数据丢失
    
    ✅ 原子性写入（安全）:
        1. 写入临时文件 (temp_xxxxx.json)
        2. 验证文件完整性（读回来检查）
        3. 备份旧文件 (results.json → results.json.backup_20260414)
        4. 原子重命名 (temp_xxxxx.json → results.json)
           ↑ 中途断电，temp 未删除但 results.json 完好
    """)
    
    # 模拟原子性写入
    print("\n模拟：安全写入 20 条结果数据")
    
    test_data = [
        {"id": f"cmt_{i:03d}", "intents": ["complaint"], "urgency": "high"}
        for i in range(1, 21)
    ]
    
    temp_fd, temp_path = tempfile.mkstemp(suffix=".json", text=True)
    try:
        # 步骤 1: 写入临时文件
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        print(f"  [步骤 1] ✓ 写入临时文件: {os.path.basename(temp_path)}")
        
        # 步骤 2: 验证完整性
        with open(temp_path, 'r', encoding='utf-8') as f:
            verify = json.load(f)
        assert len(verify) == 20
        print(f"  [步骤 2] ✓ 验证完整性: {len(verify)} 条数据可读")
        
        # 步骤 3: 备份旧文件
        demo_output = "demo_results.json"
        if os.path.exists(demo_output):
            backup_path = demo_output + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(demo_output, backup_path)
            print(f"  [步骤 3] ✓ 备份旧文件: {os.path.basename(backup_path)}")
        else:
            print(f"  [步骤 3] ⊘ 无旧文件，跳过备份")
        
        # 步骤 4: 原子重命名
        os.rename(temp_path, demo_output)
        print(f"  [步骤 4] ✓ 原子重命名完成")
        
        # 验证
        with open(demo_output, 'r') as f:
            final = json.load(f)
        print(f"\n最终验证: {demo_output} 包含 {len(final)} 条数据 ✓")
        
        # 清理
        os.remove(demo_output)
        print("清理演示文件完成")
        
    except Exception as e:
        print(f"❌ 写入失败: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def demo_checkpoint_recovery():
    """演示检查点恢复机制"""
    print("\n" + "="*60)
    print("演示 3️⃣: 检查点恢复 (Checkpoint Recovery)")
    print("="*60)
    
    print("""
    场景：处理 100 条数据，在第 67 条时 API 服务崩溃
    
    ❌ 无检查点:
        第 1 次运行：处理 1-100，在第 67 条失败
        → 前 66 条成功结果丢失，需重新处理
        
        第 2 次运行：重新处理 1-100（重复调用 66 条，浪费!)
        → 最终花费 2 倍时间和 API 配额
    
    ✅ 有检查点:
        第 1 次运行：处理 1-100，每 5 条保存检查点
        → 在第 67 条失败
        → checkpoint_001.json (1-5)
        → checkpoint_002.json (6-10)
        → ... checkpoint_013.json (61-65)
        
        第 2 次运行：指定 --start-id cmt_067 继续
        → 只处理 67-100（跳过前 66 条）
        → 加载 checkpoint_013 的结果，追加新结果
        → 最终花费 1.3 倍时间，省约 33% 配额
    """)
    
    # 模拟检查点保存
    print("\n模拟：每处理 5 条保存一个检查点")
    
    checkpoint_dir = "demo_checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    checkpoint_num = 0
    for i in range(1, 21):
        if i % 5 == 0:
            checkpoint_num += 1
            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "checkpoint_num": checkpoint_num,
                "items_processed": i,
                "results_count": i,
                "failed_count": 0,
            }
            checkpoint_file = os.path.join(checkpoint_dir, f"checkpoint_{checkpoint_num:03d}.json")
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            print(f"  [第 {i:2d} 条] 保存检查点 {checkpoint_num}: {os.path.basename(checkpoint_file)}")
        else:
            status = "✓" if i % 5 != 0 else "💾"
            print(f"  [第 {i:2d} 条] {status} 处理中")
    
    print(f"\n生成的检查点文件:")
    for file in sorted(os.listdir(checkpoint_dir)):
        print(f"  ✓ {file}")
    
    # 恢复场景
    print("\n恢复场景：从第 11 条继续")
    print(f"  1. 加载最近的检查点: checkpoint_002.json (已处理 1-10)")
    print(f"  2. 继续处理 11-20")
    print(f"  3. 所有成功结果合并，无重复")
    
    # 清理
    import shutil
    shutil.rmtree(checkpoint_dir)
    print("\n清理演示文件完成")

def main():
    print("\n" + "╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  Lesson 11: 部署前安全防护 (Pre-Deployment Safeguards)  ║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    demo_timeout_protection()
    demo_atomic_write()
    demo_checkpoint_recovery()
    
    print("\n" + "="*60)
    print("演示总结")
    print("="*60)
    print("""
    ✅ 3 大安全防护的作用:
    
    1️⃣  超时保护 (Timeout Protection)
        → 避免 API 超时导致进程卡住
        → 超时项自动记录为失败，继续处理下一项
    
    2️⃣  原子性写入 (Atomic Write)
        → 中途断电不会损坏结果文件
        → 旧数据自动备份，可以回滚
    
    3️⃣  检查点恢复 (Checkpoint Recovery)
        → 失败后可从检查点继续，无需重复处理
        → 减少 API 成本，节省时间
    
    运行实际测试:
    → python CustomerService.py --overwrite --sleep 0.1
    → 查看 results.json, failed.json, checkpoint_*.json
    """)

if __name__ == "__main__":
    main()

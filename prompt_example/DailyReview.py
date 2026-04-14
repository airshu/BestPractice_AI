#!/usr/bin/env python3
"""
Lesson 12.1: 日常样本审核 (Daily Sample Review)
监督学习的最小环：人工抽检 → 发现问题 → 反馈给模型团队 → 改进

核心思想：
每天从生产环境抽取 N 条样本，人工审核，对比与模型预测的差异。
这是发现"模型没想到"的错误模式的唯一方式。
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Tuple

def load_predictions(results_file: str = "results.json") -> List[Dict]:
    """加载模型预测结果"""
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def load_comments(comments_file: str = "comments.json") -> Dict[str, str]:
    """加载原始评论，用于人工审核"""
    try:
        with open(comments_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['id']: item['text'] for item in data}
    except FileNotFoundError:
        return {}

def daily_sample_review(sample_size: int = 5, seed: int = None) -> Dict:
    """
    Lesson 12.1: 日常样本审核
    
    步骤：
    1. 从昨日生产结果中随机抽取 N 条
    2. 取出原始评论文本
    3. 人工标注（模拟）
    4. 对比模型预测 vs 人工标注
    5. 记录差异项
    """
    print("\n" + "="*70)
    print("Lesson 12.1: 日常样本审核 (Daily Sample Review)")
    print("="*70)
    
    predictions = load_predictions()
    comments = load_comments()
    
    if not predictions:
        print("❌ 无预测结果，请先运行 CustomerService.py")
        return {}
    
    # 随机抽样
    if seed:
        random.seed(seed)
    
    sample_size = min(sample_size, len(predictions))
    sampled = random.sample(predictions, sample_size)
    
    print(f"\n📋 从 {len(predictions)} 条预测中随机抽取 {sample_size} 条进行人工审核\n")
    
    discrepancies = []
    
    for idx, pred in enumerate(sampled, 1):
        item_id = pred.get("id")
        comment_text = comments.get(item_id, "")
        pred_intents = set(pred.get("intents", []))
        pred_urgency = pred.get("urgency")
        pred_next_action = pred.get("next_action")
        
        print(f"[样本 {idx}/{sample_size}] {item_id}")
        print(f"  评论: {comment_text[:60]}...")
        print(f"  模型预测:")
        print(f"    - 意图: {pred_intents or '(无)'}")
        print(f"    - 紧急度: {pred_urgency}")
        print(f"    - 下一步: {pred_next_action[:20]}...")
        
        # 模拟人工审核（实际需要人工打标）
        # 这里用启发式规则演示异议项
        issues = []
        
        # 检查问题 1: 是否遗漏了明显的意图
        if "退款" in comment_text or "退货" in comment_text:
            if "refund_request" not in pred_intents:
                issues.append("MISSED: refund_request (评论明确提及退款)")
        
        # 检查问题 2: 紧急度是否合理
        if "急" in comment_text or "今天" in comment_text:
            if pred_urgency != "high":
                issues.append(f"URGENCY_MISMATCH: 预测={pred_urgency}, 应为=high (评论含时间紧迫)")
        
        # 检查问题 3: next_action 是否过于简单
        if len(pred_next_action) < 5:
            issues.append("ACTION_TOO_BRIEF: 下一步行动描述过于简短")
        
        if issues:
            print(f"  ⚠️  人工审核发现的问题:")
            for issue in issues:
                print(f"      - {issue}")
            discrepancies.append({
                "id": item_id,
                "comment": comment_text[:100],
                "predicted": {
                    "intents": list(pred_intents),
                    "urgency": pred_urgency,
                    "next_action": pred_next_action
                },
                "issues": issues
            })
        else:
            print(f"  ✅ 人工审核通过")
        
        print()
    
    # 生成每日审核报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sample_size": sample_size,
        "total_predictions": len(predictions),
        "discrepancies_found": len(discrepancies),
        "discrepancy_rate": f"{len(discrepancies)/sample_size*100:.1f}%",
        "discrepancies": discrepancies
    }
    
    # 保存日审核报告
    report_file = f"daily_review_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("="*70)
    print(f"✅ 日审核完成")
    print(f"   - 样本量: {sample_size}")
    print(f"   - 发现问题: {len(discrepancies)} 项")
    print(f"   - 问题率: {len(discrepancies)/sample_size*100:.1f}%")
    print(f"   - 报告已保存: {report_file}")
    print("="*70)
    
    return report

if __name__ == "__main__":
    # 示例：每天审核 5 条样本
    report = daily_sample_review(sample_size=5, seed=42)
    
    if report.get("discrepancies"):
        print("\n🔴 发现的异议项需要反馈给模型团队进行改进！")

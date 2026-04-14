#!/usr/bin/env python3
"""
Lesson 12.3: 周报数据分析 (Weekly Analytics Report)
汇总一周的监控数据，生成趋势分析和改进建议。

核心思想：
每周生成一份综合报告，包括：
- 周处理量和成功率
- 周内指标趋势
- 高频错误模式
- 人工审核的关键发现
- 改进建议
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter

def load_daily_reviews() -> List[Dict]:
    """加载本周的日审核报告"""
    reviews = []
    today = datetime.now()
    
    for i in range(7):  # 查找近 7 天的报告
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        report_file = f"daily_review_{date}.json"
        if os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    reviews.append(json.load(f))
            except:
                pass
    
    return reviews

def load_metric_history() -> List[Dict]:
    """加载指标历史"""
    try:
        with open("metric_history.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 只取最近 7 天
            return data[-7:] if len(data) > 7 else data
    except FileNotFoundError:
        return []

def load_evaluation_report() -> Dict:
    """加载最新评估报告"""
    try:
        with open("evaluation_report.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def generate_weekly_report() -> Dict:
    """
    Lesson 12.3: 周报数据分析
    
    步骤：
    1. 汇总本周的日审核数据
    2. 分析指标趋势
    3. 提取高频错误模式
    4. 生成改进建议
    5. 生成周报
    """
    
    print("\n" + "="*70)
    print("Lesson 12.3: 周报数据分析 (Weekly Analytics Report)")
    print("="*70)
    
    daily_reviews = load_daily_reviews()
    metric_history = load_metric_history()
    current_eval = load_evaluation_report()
    
    # 汇总周数据
    total_samples_reviewed = sum(r.get("sample_size", 0) for r in daily_reviews)
    total_discrepancies = sum(r.get("discrepancies_found", 0) for r in daily_reviews)
    avg_discrepancy_rate = (
        total_discrepancies / total_samples_reviewed * 100
        if total_samples_reviewed > 0 else 0
    )
    
    print(f"\n📊 周概览")
    print("-" * 70)
    print(f"  样本审核日数: {len(daily_reviews)} 天")
    print(f"  样本总数: {total_samples_reviewed} 条")
    print(f"  发现问题: {total_discrepancies} 项")
    print(f"  平均问题率: {avg_discrepancy_rate:.1f}%")
    
    # 分析高频错误模式
    print(f"\n🔍 高频错误模式")
    print("-" * 70)
    
    error_patterns = Counter()
    all_issues = []
    
    for review in daily_reviews:
        for disc in review.get("discrepancies", []):
            for issue in disc.get("issues", []):
                all_issues.append(issue)
                # 提取错误类型
                if "MISSED" in issue:
                    error_patterns["遗漏意图标签"] += 1
                elif "URGENCY_MISMATCH" in issue:
                    error_patterns["紧急度判断错误"] += 1
                elif "ACTION" in issue:
                    error_patterns["下一步行动不足"] += 1
    
    if error_patterns:
        for pattern, count in error_patterns.most_common(5):
            print(f"  #1 {pattern:20s}: {count:3d} 次")
    else:
        print("  ✅ 未发现频繁错误模式")
    
    # 分析指标趋势
    print(f"\n📈 指标周趋势")
    print("-" * 70)
    
    if metric_history:
        first_record = metric_history[0]
        last_record = metric_history[-1]
        
        for metric in ["intent_f1", "urgency_accuracy", "next_action_pass"]:
            start_val = first_record.get(metric, 0)
            end_val = last_record.get(metric, 0)
            change = end_val - start_val
            change_pct = (change / start_val * 100) if start_val > 0 else 0
            
            trend = "📈 上升" if change > 0 else "📉 下降" if change < 0 else "➡️  持平"
            print(f"  {trend:12s} {metric:20s}: {start_val:.4f} → {end_val:.4f} ({change:+.4f})")
    else:
        print("  ⊘ 无足够的历史数据")
    
    # 改进建议
    print(f"\n💡 改进建议")
    print("-" * 70)
    
    recommendations = []
    
    if error_patterns.get("遗漏意图标签", 0) > 0:
        recommendations.append(
            "1. 强化意图识别：review MAIN_PROMPT 中的意图定义，补充触发示例"
        )
    
    if error_patterns.get("紧急度判断错误", 0) > 0:
        recommendations.append(
            "2. 优化紧急度规则：添加更多时间触发词（如'急'、'今天'等）"
        )
    
    if current_eval.get("Urgency_Accuracy", 0) < 0.88:
        recommendations.append(
            "3. 进行 A/B 测试：对比当前 prompt 与改进 prompt 的效果"
        )
    
    if not recommendations:
        recommendations.append("✅ 当前系统运行正常，继续监控")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    # 生成周报文件
    weekly_report = {
        "timestamp": datetime.now().isoformat(),
        "week": datetime.now().strftime("%Y-W%V"),
        "summary": {
            "days_monitored": len(daily_reviews),
            "samples_reviewed": total_samples_reviewed,
            "discrepancies_found": total_discrepancies,
            "avg_discrepancy_rate": f"{avg_discrepancy_rate:.1f}%",
        },
        "error_patterns": dict(error_patterns.most_common(5)),
        "metric_trend": {
            "start": metric_history[0] if metric_history else None,
            "end": metric_history[-1] if metric_history else None,
        },
        "recommendations": recommendations,
        "data_sources": {
            "daily_reviews": len(daily_reviews),
            "metric_points": len(metric_history),
        }
    }
    
    # 保存周报
    report_file = f"weekly_report_{datetime.now().strftime('%Y_W%V')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(weekly_report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print(f"✅ 周报已生成: {report_file}")
    print("="*70)
    
    return weekly_report

if __name__ == "__main__":
    report = generate_weekly_report()
    
    print("\n📋 周报使用建议：")
    print("   1. 每周一自动运行本脚本")
    print("   2. 周报发送给 PM/QA 团队审核")
    print("   3. 根据建议安排下周的优化计划")
    print("   4. 优化后再验证效果，形成持续改进环")

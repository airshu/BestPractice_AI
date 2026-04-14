#!/usr/bin/env python3
"""
Lesson 12.2: 指标漂移检测 (Metric Drift Detection)
监控系统质量的核心指标，当精度下降时自动告警。

核心思想：
每次运行评估，对比当前指标与历史基线。
如果下降超过阈值，发出告警。
这样可以及早发现"无声的衰退"。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

def load_evaluation_report(report_file: str = "evaluation_report.json") -> Dict:
    """加载最新的评估报告"""
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_metric_history(history_file: str = "metric_history.json") -> List[Dict]:
    """加载历史指标记录"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def detect_metric_drift(
    thresholds: Dict = None,
    min_history_points: int = 3
) -> Dict:
    """
    Lesson 12.2: 指标漂移检测
    
    步骤：
    1. 加载当前评估结果
    2. 加载历史指标
    3. 对比当前 vs 基线
    4. 检测异常（下降超过阈值）
    5. 生成告警
    
    关键指标：
    - Intent Precision (目标: >= 0.88)
    - Intent Recall (目标: >= 0.92)
    - Intent F1 (目标: >= 0.90)
    - Urgency Accuracy (目标: >= 0.88)
    - Next Action Pass (目标: >= 0.95)
    """
    
    if thresholds is None:
        thresholds = {
            "intent_precision": 0.88,
            "intent_recall": 0.92,
            "intent_f1": 0.90,
            "urgency_accuracy": 0.88,
            "next_action_pass": 0.95,
        }
    
    print("\n" + "="*70)
    print("Lesson 12.2: 指标漂移检测 (Metric Drift Detection)")
    print("="*70)
    
    current = load_evaluation_report()
    history = load_metric_history()
    
    if not current:
        print("❌ 无当前评估报告，请先运行 Evaluator.py")
        return {}
    
    # 提取当前指标
    current_metrics = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "intent_precision": current.get("Precision", 0),
        "intent_recall": current.get("Recall", 0),
        "intent_f1": current.get("F1", 0),
        "urgency_accuracy": current.get("Urgency_Accuracy", 0),
        "next_action_pass": current.get("Next_Action_Pass", 0),
    }
    
    print(f"\n📊 当前指标 ({current_metrics['date']})")
    print("-" * 70)
    for metric, value in current_metrics.items():
        if metric not in ["timestamp", "date"]:
            threshold = thresholds.get(metric, 0)
            status = "✅" if value >= threshold else "⚠️ "
            print(f"  {status} {metric:25s}: {value:.4f} (目标: {threshold:.2f})")
    
    # 与历史对比
    alerts = []
    
    if history:
        print(f"\n📈 历史对比 (共 {len(history)} 个历史数据点)")
        print("-" * 70)
        
        last_record = history[-1]
        
        for metric in ["intent_precision", "intent_recall", "intent_f1", 
                       "urgency_accuracy", "next_action_pass"]:
            current_val = current_metrics.get(metric, 0)
            previous_val = last_record.get(metric, 0)
            threshold = thresholds.get(metric, 0)
            
            change = current_val - previous_val
            change_pct = (change / previous_val * 100) if previous_val > 0 else 0
            
            # 告警规则
            alert_reasons = []
            
            # 规则 1: 低于目标值
            if current_val < threshold:
                alert_reasons.append(f"低于目标 ({threshold:.2f})")
            
            # 规则 2: 相比前次下降 > 5%
            if change < 0 and abs(change_pct) > 5:
                alert_reasons.append(f"环比下降 {abs(change_pct):.1f}%")
            
            if alert_reasons:
                status = "🔴"
                alerts.append({
                    "metric": metric,
                    "current": current_val,
                    "previous": previous_val,
                    "threshold": threshold,
                    "change": change,
                    "change_pct": change_pct,
                    "reasons": alert_reasons
                })
            else:
                status = "✅" if current_val >= threshold else "⚠️ "
            
            print(f"  {status} {metric:25s}: {current_val:.4f} "
                  f"(前次: {previous_val:.4f}, 变化: {change:+.4f}, {change_pct:+.1f}%)")
    
    # 生成漂移检测报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "current_metrics": current_metrics,
        "thresholds": thresholds,
        "alerts_count": len(alerts),
        "alerts": alerts,
        "alert_level": "CRITICAL" if len(alerts) >= 3 else "WARNING" if len(alerts) > 0 else "OK"
    }
    
    # 保存漂移检测报告
    report_file = f"metric_drift_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print(f"📋 检测结果: {report['alert_level']}")
    if alerts:
        print(f"   🔴 发现 {len(alerts)} 个告警项:")
        for alert in alerts:
            print(f"      - {alert['metric']}: {', '.join(alert['reasons'])}")
    else:
        print(f"   ✅ 所有指标正常")
    print(f"   报告已保存: {report_file}")
    print("="*70)
    
    # 更新历史记录
    history.append(current_metrics)
    
    # 只保留最近 30 天的记录
    history = history[-30:]
    
    with open("metric_history.json", 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    return report

if __name__ == "__main__":
    report = detect_metric_drift()
    
    if report.get("alerts"):
        print("\n🚨 需要采取行动：")
        print("   1. 分析告警原因")
        print("   2. 审查最近的预测样本")
        print("   3. 考虑更新模型或 prompt")
        print("   4. 进行 A/B 测试验证改进")

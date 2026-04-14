#!/usr/bin/env python3
"""
Lesson 12: 后发大监控 (Post-Launch Monitoring)
监控中枢 - 一个脚本启动所有监控任务
"""

import os
import sys
import argparse
from datetime import datetime
from importlib import import_module

def run_daily_monitoring():
    """运行日常监控任务"""
    print("\n" + "🔵 "*35)
    print("\n               🔵 启动日常监控任务 🔵")
    print("\n" + "🔵 "*35 + "\n")
    
    try:
        DailyReview = import_module("DailyReview")
        report = DailyReview.daily_sample_review(sample_size=5, seed=None)
        return report
    except Exception as e:
        print(f"❌ 日常审核失败: {e}")
        return None

def run_drift_detection():
    """运行指标漂移检测"""
    print("\n" + "🟠 "*35)
    print("\n               🟠 启动漂移检测任务 🟠")
    print("\n" + "🟠 "*35 + "\n")
    
    try:
        MetricDrift = import_module("MetricDriftDetection")
        report = MetricDrift.detect_metric_drift()
        return report
    except Exception as e:
        print(f"❌ 漂移检测失败: {e}")
        return None

def run_weekly_report():
    """运行周报生成"""
    print("\n" + "🟡 "*35)
    print("\n               🟡 生成周报任务 🟡")
    print("\n" + "🟡 "*35 + "\n")
    
    try:
        Weekly = import_module("WeeklyReport")
        report = Weekly.generate_weekly_report()
        return report
    except Exception as e:
        print(f"❌ 周报生成失败: {e}")
        return None


def run_prompt_ab_test():
    """运行 Prompt A/B 测试"""
    print("\n" + "🟣 "*35)
    print("\n               🟣 启动 Prompt A/B 测试 🟣")
    print("\n" + "🟣 "*35 + "\n")

    try:
        AB = import_module("PromptABTest")
        AB.main()
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ A/B 测试失败: {e}")
        return None


def run_rollout_gate():
    """运行灰度发布门禁与回滚策略决策"""
    print("\n" + "🟤 "*35)
    print("\n               🟤 启动灰度发布门禁决策 🟤")
    print("\n" + "🟤 "*35 + "\n")

    try:
        Rollout = import_module("RolloutDecision")
        Rollout.main([])
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ 灰度门禁决策失败: {e}")
        return None


def run_progressive_rollout():
    """运行灰度升档检查"""
    print("\n" + "🟢 "*35)
    print("\n               🟢 启动灰度升档检查 🟢")
    print("\n" + "🟢 "*35 + "\n")

    try:
        Ramp = import_module("ProgressiveRollout")
        Ramp.main([])
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ 灰度升档检查失败: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Lesson 12-13: 监控与A/B测试中枢")
    parser.add_argument(
        "--run",
        type=str,
        choices=["daily", "drift", "weekly", "ab", "rollout", "ramp", "all"],
        default="all",
        help="运行指定的监控任务 (default: all)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("Lesson 12: 后发大监控 (Post-Launch Monitoring)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    tasks = []
    
    if args.run in ["all", "daily"]:
        tasks.append(("日常样本审核", run_daily_monitoring))
    
    if args.run in ["all", "drift"]:
        tasks.append(("指标漂移检测", run_drift_detection))
    
    if args.run in ["all", "weekly"]:
        tasks.append(("周报数据分析", run_weekly_report))

    if args.run in ["all", "ab"]:
        tasks.append(("Prompt A/B 测试", run_prompt_ab_test))

    if args.run in ["all", "rollout"]:
        tasks.append(("灰度发布门禁决策", run_rollout_gate))

    if args.run in ["all", "ramp"]:
        tasks.append(("灰度升档检查", run_progressive_rollout))
    
    results = {}
    for name, func in tasks:
        results[name] = func()
    
    # 总结
    print("\n" + "="*70)
    print("📋 监控执行总结")
    print("="*70)
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    print("="*70)

if __name__ == "__main__":
    main()

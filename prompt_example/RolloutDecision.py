#!/usr/bin/env python3
import argparse
import glob
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_latest_ab_report() -> Optional[str]:
    candidates = sorted(glob.glob("ab_test_report_*.json"))
    if not candidates:
        return None
    return candidates[-1]


def safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def evaluate_gate(report: Dict[str, Any]) -> Dict[str, Any]:
    decision = report.get("decision", {})
    m1 = report.get("report_v1", {}).get("metrics", {})
    m2 = report.get("report_v2", {}).get("metrics", {})
    sample_size = int(report.get("sample_size", 0))

    failures_v1 = report.get("failures_v1", []) or []
    failures_v2 = report.get("failures_v2", []) or []
    fail_rate_v1 = safe_rate(len(failures_v1), sample_size)
    fail_rate_v2 = safe_rate(len(failures_v2), sample_size)

    # 上线门禁策略（可按业务调整）
    gates = {
        "min_sample_size": sample_size >= 20,
        "winner_is_v2": decision.get("winner") == "v2",
        "v2_intent_f1_floor": float(m2.get("intent_f1", 0)) >= 0.90,
        "v2_urgency_floor": float(m2.get("urgency_accuracy", 0)) >= 0.88,
        "v2_action_floor": float(m2.get("next_action_pass_rate", 0)) >= 0.95,
        "v2_not_worse_urgency": float(m2.get("urgency_accuracy", 0)) >= float(m1.get("urgency_accuracy", 0)) - 0.01,
        "v2_not_worse_action": float(m2.get("next_action_pass_rate", 0)) >= float(m1.get("next_action_pass_rate", 0)) - 0.02,
        "v2_fail_rate_ok": fail_rate_v2 <= 0.05,
    }

    passed = all(gates.values())
    failed_rules = [rule for rule, ok in gates.items() if not ok]

    if passed:
        action = "promote_v2_canary_10pct"
    else:
        action = "keep_v1"

    # 预定义回滚触发器（用于灰度上线后）
    rollback_triggers = {
        "intent_f1_drop": "v2 线上7日滚动 intent_f1 较 v1 下降 > 0.02",
        "urgency_drop": "v2 线上 urgency_accuracy 低于 0.85 持续2天",
        "action_drop": "v2 线上 next_action_pass_rate 低于 0.93",
        "failure_spike": "v2 API失败率 > 8% 持续30分钟",
    }

    rollout_plan = [
        "10% 流量灰度 24 小时，观察关键指标",
        "若全部通过，提升到 30% 流量 24 小时",
        "若全部通过，提升到 70% 流量 24 小时",
        "最后全量发布并保留 v1 回退开关",
    ]

    return {
        "timestamp": datetime.now().isoformat(),
        "sample_size": sample_size,
        "decision": action,
        "gates": gates,
        "failed_rules": failed_rules,
        "summary": {
            "winner": decision.get("winner"),
            "score_v1": decision.get("score_v1"),
            "score_v2": decision.get("score_v2"),
            "fail_rate_v1": round(fail_rate_v1, 4),
            "fail_rate_v2": round(fail_rate_v2, 4),
        },
        "rollback_triggers": rollback_triggers,
        "rollout_plan": rollout_plan,
    }


def print_decision(result: Dict[str, Any], report_path: str) -> None:
    print("=" * 60)
    print("Rollout Gate Decision")
    print("=" * 60)
    print(f"Report: {report_path}")
    print(f"Sample Size: {result['sample_size']}")
    print(f"Decision: {result['decision']}")
    print("-" * 60)
    print("Gate Checks:")
    for rule, ok in result["gates"].items():
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {rule}")

    if result["failed_rules"]:
        print("-" * 60)
        print("Failed Rules:")
        for item in result["failed_rules"]:
            print(f"  - {item}")

    print("-" * 60)
    print("Rollback Triggers:")
    for key, text in result["rollback_triggers"].items():
        print(f"  - {key}: {text}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollout gate and rollback decision from A/B report")
    parser.add_argument("--report", type=str, default="", help="A/B report path, default uses latest ab_test_report_*.json")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    report_path = args.report or find_latest_ab_report()
    if not report_path:
        raise RuntimeError("No A/B report found. Run PromptABTest.py first.")

    report = load_json(report_path)
    result = evaluate_gate(report)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"rollout_decision_{stamp}.json"
    with open(out_file, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print_decision(result, report_path)
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()

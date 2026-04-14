#!/usr/bin/env python3
import argparse
import glob
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


STAGE_ORDER = [10, 30, 70, 100]


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def latest_file(pattern: str) -> Optional[str]:
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def next_stage(current_stage: int) -> int:
    if current_stage not in STAGE_ORDER:
        raise ValueError(f"Invalid stage: {current_stage}. valid={STAGE_ORDER}")
    idx = STAGE_ORDER.index(current_stage)
    if idx + 1 >= len(STAGE_ORDER):
        return current_stage
    return STAGE_ORDER[idx + 1]


def evaluate_promotion(current_stage: int, rollout: Dict[str, Any], drift: Dict[str, Any]) -> Dict[str, Any]:
    target = next_stage(current_stage)

    decision = rollout.get("decision", "keep_v1")
    failed_rules = rollout.get("failed_rules", [])
    drift_level = drift.get("alert_level", "UNKNOWN")
    alerts_count = int(drift.get("alerts_count", 0))

    checks = {
        "gate_allow_promote": decision == "promote_v2_canary_10pct",
        "no_failed_gate_rule": len(failed_rules) == 0,
        "drift_not_critical": drift_level != "CRITICAL",
        "drift_alerts_le_1": alerts_count <= 1,
    }

    passed = all(checks.values())
    recommendation = f"promote_to_{target}pct" if passed and target != current_stage else "hold_stage"

    if current_stage == 100:
        recommendation = "full_rollout_already"

    reasons = []
    if not checks["gate_allow_promote"]:
        reasons.append("A/B门禁未允许发布")
    if not checks["no_failed_gate_rule"]:
        reasons.append(f"存在门禁失败规则: {', '.join(failed_rules)}")
    if not checks["drift_not_critical"]:
        reasons.append("漂移告警级别为CRITICAL")
    if not checks["drift_alerts_le_1"]:
        reasons.append(f"漂移告警数量过多: {alerts_count}")
    if not reasons:
        reasons.append("全部检查通过")

    return {
        "timestamp": datetime.now().isoformat(),
        "current_stage": current_stage,
        "target_stage": target,
        "recommendation": recommendation,
        "checks": checks,
        "reasons": reasons,
        "inputs": {
            "rollout_decision": decision,
            "drift_alert_level": drift_level,
            "drift_alerts_count": alerts_count,
        },
    }


def print_result(result: Dict[str, Any], rollout_file: str, drift_file: str) -> None:
    print("=" * 64)
    print("Progressive Rollout Check")
    print("=" * 64)
    print(f"Rollout file: {rollout_file}")
    print(f"Drift file:   {drift_file}")
    print(f"Current: {result['current_stage']}% -> Target: {result['target_stage']}%")
    print(f"Recommendation: {result['recommendation']}")
    print("-" * 64)
    for key, ok in result["checks"].items():
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {key}")
    print("-" * 64)
    print("Reasons:")
    for reason in result["reasons"]:
        print(f"- {reason}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Progressive rollout stage checker")
    parser.add_argument("--stage", type=int, default=10, help="Current traffic stage: 10|30|70|100")
    parser.add_argument("--rollout-file", type=str, default="", help="rollout_decision_*.json path")
    parser.add_argument("--drift-file", type=str, default="", help="metric_drift_*.json path")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    rollout_file = args.rollout_file or latest_file("rollout_decision_*.json")
    drift_file = args.drift_file or latest_file("metric_drift_*.json")

    if not rollout_file:
        raise RuntimeError("No rollout decision file found. Run RolloutDecision.py first.")
    if not drift_file:
        raise RuntimeError("No metric drift file found. Run MetricDriftDetection.py first.")

    rollout = load_json(rollout_file)
    drift = load_json(drift_file)
    result = evaluate_promotion(args.stage, rollout, drift)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"progressive_rollout_{stamp}.json"
    with open(out_file, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print_result(result, rollout_file, drift_file)
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()

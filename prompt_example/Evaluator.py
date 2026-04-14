import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


ALLOWED_INTENTS = {
    "refund_request",
    "exchange_request",
    "product_defect",
    "manual_support",
    "complaint",
}


def load_json(file_name: str) -> Any:
    path = Path(file_name)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {item["id"]: item for item in items}


def safe_set(values: List[str]) -> Set[str]:
    return set(values or [])


def compute_intent_counts(predicted: Set[str], gold: Set[str]) -> Tuple[int, int, int]:
    true_positive = len(predicted & gold)
    false_positive = len(predicted - gold)
    false_negative = len(gold - predicted)
    return true_positive, false_positive, false_negative


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def score_next_action(action: str) -> Dict[str, Any]:
    text = (action or "").strip()
    has_value = bool(text)
    within_length = len(text) <= 30
    actionable_keywords = [
        "联系", "核实", "补发", "退款", "换货", "发送", "提供", "协助", "致歉", "安排", "跟进", "处理",
    ]
    actionable = any(keyword in text for keyword in actionable_keywords)
    passed = has_value and within_length and actionable
    return {
        "passed": passed,
        "has_value": has_value,
        "within_length": within_length,
        "actionable": actionable,
    }


def evaluate(predictions: List[Dict[str, Any]], gold_labels: List[Dict[str, Any]]) -> Dict[str, Any]:
    prediction_map = index_by_id(predictions)
    gold_map = index_by_id(gold_labels)

    common_ids = sorted(set(prediction_map) & set(gold_map))
    missing_prediction_ids = sorted(set(gold_map) - set(prediction_map))
    extra_prediction_ids = sorted(set(prediction_map) - set(gold_map))

    total_tp = 0
    total_fp = 0
    total_fn = 0
    urgency_correct = 0
    next_action_passed = 0
    details = []

    for item_id in common_ids:
        prediction = prediction_map[item_id]
        gold = gold_map[item_id]

        predicted_intents = safe_set(prediction.get("intents", []))
        gold_intents = safe_set(gold.get("intents", []))
        tp, fp, fn = compute_intent_counts(predicted_intents, gold_intents)
        total_tp += tp
        total_fp += fp
        total_fn += fn

        urgency_hit = prediction.get("urgency") == gold.get("urgency")
        if urgency_hit:
            urgency_correct += 1

        next_action_check = score_next_action(prediction.get("next_action", ""))
        if next_action_check["passed"]:
            next_action_passed += 1

        details.append(
            {
                "id": item_id,
                "predicted_intents": sorted(predicted_intents),
                "gold_intents": sorted(gold_intents),
                "missed_intents": sorted(gold_intents - predicted_intents),
                "extra_intents": sorted(predicted_intents - gold_intents),
                "predicted_urgency": prediction.get("urgency"),
                "gold_urgency": gold.get("urgency"),
                "urgency_correct": urgency_hit,
                "next_action": prediction.get("next_action", ""),
                "next_action_check": next_action_check,
            }
        )

    precision = safe_divide(total_tp, total_tp + total_fp)
    recall = safe_divide(total_tp, total_tp + total_fn)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    urgency_accuracy = safe_divide(urgency_correct, len(common_ids))
    next_action_pass_rate = safe_divide(next_action_passed, len(common_ids))

    return {
        "coverage": {
            "gold_count": len(gold_labels),
            "prediction_count": len(predictions),
            "evaluated_count": len(common_ids),
            "missing_prediction_ids": missing_prediction_ids,
            "extra_prediction_ids": extra_prediction_ids,
        },
        "metrics": {
            "intent_precision": round(precision, 4),
            "intent_recall": round(recall, 4),
            "intent_f1": round(f1, 4),
            "urgency_accuracy": round(urgency_accuracy, 4),
            "next_action_pass_rate": round(next_action_pass_rate, 4),
        },
        "details": details,
    }


def print_report(report: Dict[str, Any]) -> None:
    coverage = report["coverage"]
    metrics = report["metrics"]
    print("=" * 60)
    print("Evaluation Report")
    print("=" * 60)
    print(f"Gold labels: {coverage['gold_count']}")
    print(f"Predictions: {coverage['prediction_count']}")
    print(f"Evaluated: {coverage['evaluated_count']}")
    print(f"Missing predictions: {coverage['missing_prediction_ids']}")
    print(f"Extra predictions: {coverage['extra_prediction_ids']}")
    print("-" * 60)
    print(f"Intent Precision: {metrics['intent_precision']:.4f}")
    print(f"Intent Recall:    {metrics['intent_recall']:.4f}")
    print(f"Intent F1:        {metrics['intent_f1']:.4f}")
    print(f"Urgency Accuracy: {metrics['urgency_accuracy']:.4f}")
    print(f"Next Action Pass: {metrics['next_action_pass_rate']:.4f}")
    print("-" * 60)

    issues = [
        detail
        for detail in report["details"]
        if detail["missed_intents"]
        or detail["extra_intents"]
        or not detail["urgency_correct"]
        or not detail["next_action_check"]["passed"]
    ]
    if not issues:
        print("No evaluation issues found.")
        return

    print("Key Issues:")
    for detail in issues:
        print(f"- {detail['id']}")
        if detail["missed_intents"]:
            print(f"  missed_intents: {detail['missed_intents']}")
        if detail["extra_intents"]:
            print(f"  extra_intents: {detail['extra_intents']}")
        if not detail["urgency_correct"]:
            print(
                f"  urgency: predicted={detail['predicted_urgency']}, gold={detail['gold_urgency']}"
            )
        if not detail["next_action_check"]["passed"]:
            print(f"  next_action: {detail['next_action']}")


def main() -> None:
    predictions = load_json("results.json")
    gold_labels = load_json("gold_labels.json")
    report = evaluate(predictions, gold_labels)
    print_report(report)

    with open("evaluation_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print("Saved detailed report to evaluation_report.json")


if __name__ == "__main__":
    main()
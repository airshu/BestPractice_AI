#!/usr/bin/env python3
import argparse
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from openai import OpenAI

from Evaluator import evaluate


PROMPT_V1 = """你是客服质检助手。请基于“用户评论”做多标签意图识别与紧急度判断。

只输出 JSON，不要输出任何额外文字，不要使用 Markdown 代码块。

输出格式：
{
  "id": "{{id}}",
  "intents": ["refund_request|exchange_request|product_defect|manual_support|complaint"],
  "urgency": "high|medium|low",
  "confidence": 0.00,
  "next_action": "..."
}

intent 定义：
- refund_request：用户明确提出退款、退货、退差价、退款意向
- exchange_request：用户明确提出换货、换新
- product_defect：用户明确描述商品故障、损坏、缺件、性能异常
- manual_support：用户明确请求说明书、教程、操作指导、安装指导
- complaint：用户明确表达对服务、产品或体验的不满、责备或投诉

严格规则：
1) intents 可多选，但只能从以下集合中选择：
   refund_request、exchange_request、product_defect、manual_support、complaint
2) 只有评论中出现明确证据时，才允许打该标签
3) 不要因为客服需要联系用户就打 manual_support
4) 不要因为用户不满就自动打 refund_request
5) 不要因为存在售后动作就自动推断额外 intent
6) 若无明确证据，不要添加对应 intent

urgency 判定：
- high：涉及安全风险、核心功能不可用、强烈退款/换货诉求、明确时间紧迫、严重影响工作生活
- medium：有明确问题或明显不满，但不紧急，且未完全阻断核心使用
- low：普通咨询、轻微体验反馈、一般好评、非紧急建议

输出规则：
1) confidence 取值 0.00~1.00，保留两位小数
2) next_action 不超过 30 字
3) next_action 必须是客服下一步可直接执行的动作
4) 优先使用动作动词开头，例如：联系、核实、发送、补发、退款、换货、安排、跟进、记录
5) 必须严格依据评论原文，不得编造

用户评论：
{{review_text}}"""

PROMPT_V2 = """你是客服质检助手。请基于“用户评论”做多标签意图识别与紧急度判断。

只输出 JSON，不要输出任何额外文字，不要使用 Markdown 代码块。

输出格式：
{
  "id": "{{id}}",
  "intents": ["refund_request|exchange_request|product_defect|manual_support|complaint"],
  "urgency": "high|medium|low",
  "confidence": 0.00,
  "next_action": "..."
}

intent 定义：
- refund_request：用户明确提出退款、退货、退差价、退款意向
- exchange_request：用户明确提出换货、换新
- product_defect：用户明确描述商品故障、损坏、缺件、性能异常
- manual_support：用户明确请求说明书、教程、操作指导、安装指导、连接配置帮助
- complaint：用户明确表达对服务、产品或体验的不满、责备或投诉

严格规则：
1) intents 可多选，但只能从以下集合中选择：
   refund_request、exchange_request、product_defect、manual_support、complaint
2) 只有评论中出现明确证据时，才允许打该标签
3) 不要因为客服需要联系用户就打 manual_support
4) 不要因为用户不满就自动打 refund_request
5) 不要因为存在售后动作就自动推断额外 intent
6) 若无明确证据，不要添加对应 intent
7) 出现“不会用/不会连接/怎么设置/教程/说明书/指导”优先考虑 manual_support

urgency 判定：
- high：涉及安全风险、核心功能不可用、强烈退款/换货诉求、明确时间紧迫、严重影响工作生活
- medium：有明确问题或明显不满，但不紧急，且未完全阻断核心使用
- low：普通咨询、轻微体验反馈、一般好评、非紧急建议

补充规则：
1) “今天必须处理 / 急用 / 严重影响工作生活 / 马上处理 / 立刻”优先判为 high
2) “客服态度差 / 回复慢 / 明显不满”通常判为 medium
3) “还能继续使用，但体验一般”通常判为 low

输出规则：
1) confidence 取值 0.00~1.00，保留两位小数
2) next_action 不超过 30 字
3) next_action 必须是客服下一步可直接执行的动作
4) 优先使用动作动词开头，例如：联系、核实、发送、补发、退款、换货、安排、跟进、记录
5) 必须严格依据评论原文，不得编造

用户评论：
{{review_text}}"""


def load_json(file_name: str) -> Any:
    with open(file_name, "r", encoding="utf-8") as file:
        return json.load(file)


def call_model(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.responses.create(model=model, input=prompt)
    return (resp.output_text or "").strip()


def try_parse_prediction(raw: str, item_id: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        data = json.loads(raw)
    except Exception:
        return False, {"id": item_id, "error": "invalid_json", "raw": raw[:120]}

    required = ["id", "intents", "urgency", "confidence", "next_action"]
    for key in required:
        if key not in data:
            return False, {"id": item_id, "error": f"missing_{key}", "raw": raw[:120]}

    return True, data


def run_prompt(
    client: OpenAI,
    model: str,
    prompt_template: str,
    comments: List[Dict[str, str]],
    sleep_sec: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    predictions: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for index, item in enumerate(comments, 1):
        item_id = item["id"]
        prompt = prompt_template.replace("{{id}}", item_id).replace("{{review_text}}", item["text"].strip())
        try:
            raw = call_model(client, model, prompt)
            ok, parsed = try_parse_prediction(raw, item_id)
            if ok:
                predictions.append(parsed)
            else:
                failures.append(parsed)
        except Exception as exc:
            failures.append({"id": item_id, "error": "api_error", "raw": str(exc)[:160]})

        if index % 5 == 0 or index == len(comments):
            print(f"[progress] {index}/{len(comments)}")
        time.sleep(sleep_sec)

    return predictions, failures


def metric_score(metrics: Dict[str, float]) -> float:
    # 业务权重：意图F1最重要，其次紧急度，再是next_action
    return (
        0.45 * metrics["intent_f1"]
        + 0.35 * metrics["urgency_accuracy"]
        + 0.20 * metrics["next_action_pass_rate"]
    )


def compare_reports(report_v1: Dict[str, Any], report_v2: Dict[str, Any]) -> Dict[str, Any]:
    m1 = report_v1["metrics"]
    m2 = report_v2["metrics"]

    deltas = {
        "intent_precision": round(m2["intent_precision"] - m1["intent_precision"], 4),
        "intent_recall": round(m2["intent_recall"] - m1["intent_recall"], 4),
        "intent_f1": round(m2["intent_f1"] - m1["intent_f1"], 4),
        "urgency_accuracy": round(m2["urgency_accuracy"] - m1["urgency_accuracy"], 4),
        "next_action_pass_rate": round(m2["next_action_pass_rate"] - m1["next_action_pass_rate"], 4),
    }

    score_v1 = metric_score(m1)
    score_v2 = metric_score(m2)

    if score_v2 > score_v1:
        winner = "v2"
    elif score_v2 < score_v1:
        winner = "v1"
    else:
        winner = "tie"

    return {
        "score_v1": round(score_v1, 4),
        "score_v2": round(score_v2, 4),
        "winner": winner,
        "deltas": deltas,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt A/B test for customer-service classifier")
    parser.add_argument("--sample-size", type=int, default=20, help="How many comments to test")
    parser.add_argument("--sleep", type=float, default=0.05, help="Sleep seconds between API calls")
    parser.add_argument("--seed", type=int, default=42, help="Reserved for future random sampling")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    model = os.environ.get("MODEL_ID")

    if not api_key or not base_url or not model:
        raise RuntimeError("Missing env vars: OPENAI_API_KEY / OPENAI_API_BASE(or OPENAI_BASE_URL) / MODEL_ID")

    comments = load_json("comments.json")
    gold_labels = load_json("gold_labels.json")
    comments = comments[: max(1, min(args.sample_size, len(comments)))]

    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"[A/B] running sample_size={len(comments)} model={model}")

    predictions_v1, failures_v1 = run_prompt(client, model, PROMPT_V1, comments, args.sleep)
    predictions_v2, failures_v2 = run_prompt(client, model, PROMPT_V2, comments, args.sleep)

    gold_subset_ids = {item["id"] for item in comments}
    gold_subset = [item for item in gold_labels if item["id"] in gold_subset_ids]

    report_v1 = evaluate(predictions_v1, gold_subset)
    report_v2 = evaluate(predictions_v2, gold_subset)
    decision = compare_reports(report_v1, report_v2)

    output = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "base_url": base_url,
        "sample_size": len(comments),
        "decision": decision,
        "report_v1": report_v1,
        "report_v2": report_v2,
        "failures_v1": failures_v1,
        "failures_v2": failures_v2,
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"ab_test_report_{stamp}.json"
    pred1_file = f"ab_results_v1_{stamp}.json"
    pred2_file = f"ab_results_v2_{stamp}.json"

    with open(out_file, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    with open(pred1_file, "w", encoding="utf-8") as file:
        json.dump(predictions_v1, file, ensure_ascii=False, indent=2)
    with open(pred2_file, "w", encoding="utf-8") as file:
        json.dump(predictions_v2, file, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("A/B Result")
    print("=" * 60)
    print(f"V1 score: {decision['score_v1']:.4f}")
    print(f"V2 score: {decision['score_v2']:.4f}")
    print(f"Winner: {decision['winner']}")
    print("Deltas(v2-v1):")
    for key, value in decision["deltas"].items():
        print(f"  {key}: {value:+.4f}")
    print(f"Saved: {out_file}")
    print(f"Saved: {pred1_file}")
    print(f"Saved: {pred2_file}")


if __name__ == "__main__":
    main()

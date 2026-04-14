import json
import time
import logging
import argparse
from typing import Any, Dict, Tuple
from openai import OpenAI
from datetime import datetime

ALLOWED_INTENTS = {
    "refund_request",
    "exchange_request",
    "product_defect",
    "manual_support",
    "complaint",
}
ALLOWED_URGENCY = {"high", "medium", "low"}

MAIN_PROMPT = """你是客服质检助手。请基于“用户评论”做多标签意图识别与紧急度判断。

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

补充规则：
1) “今天必须处理 / 急用 / 严重影响工作生活”优先判为 high
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

REPAIR_PROMPT = """你是 JSON 修复器。
请把下面内容修复为合法 JSON，保持原始语义不变，不新增不存在的信息。
只输出修复后的 JSON，不要输出解释。

待修复内容：
{{broken_output}}"""

def validate_item(data: Dict[str, Any]) -> Tuple[bool, str]:
    required = ["id", "intents", "urgency", "confidence", "next_action"]
    for k in required:
        if k not in data:
            return False, f"missing_field:{k}"

    if not isinstance(data["intents"], list) or any(i not in ALLOWED_INTENTS for i in data["intents"]):
        return False, "invalid_intents"

    if data["urgency"] not in ALLOWED_URGENCY:
        return False, "invalid_urgency"

    try:
        conf = float(data["confidence"])
    except Exception:
        return False, "invalid_confidence_type"
    if not (0 <= conf <= 1):
        return False, "invalid_confidence_range"

    if len(str(data["next_action"])) > 30:
        return False, "next_action_too_long"

    return True, "ok"

def call_model(client: OpenAI, model: str, prompt: str) -> str:
    logger = logging.getLogger(__name__)
    logger.debug(f"[Model Call] model={model}, prompt_len={len(prompt)}")
    try:
        resp = client.responses.create(model=model, input=prompt)
        result = resp.output_text.strip()
        logger.debug(f"[Model Success] output_len={len(result)}, first_100_chars={result[:100]}")
        return result
    except Exception as e:
        logger.error(f"[Model Error] {str(e)}")
        raise

def parse_json(text: str):
    return json.loads(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Customer service comment classifier")
    parser.add_argument(
        "--start-id",
        type=str,
        default=None,
        help="Resume processing from this comment id (inclusive), e.g. cmt_006",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Sleep seconds between items to avoid rate spikes",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ignore existing results.json and failed.json and start fresh",
    )
    return parser.parse_args()


def load_existing(file_name: str) -> list:
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def build_start_index(items: list, start_id: str | None) -> int:
    if not start_id:
        return 0
    for index, item in enumerate(items):
        if item.get("id") == start_id:
            return index
    raise ValueError(f"start id not found in comments.json: {start_id}")


def ordered_by_comments(items: list, data_map: Dict[str, Dict[str, Any]]) -> list:
    ordered = []
    for item in items:
        item_id = item.get("id")
        if item_id in data_map:
            ordered.append(data_map[item_id])
    return ordered

def process_one(client: OpenAI, model: str, item: Dict[str, str], max_retry: int = 2):
    logger = logging.getLogger(__name__)
    item_id = item["id"]
    logger.info(f"[Processing] id={item_id}, text_len={len(item['text'])}")
    
    # 1) 主调用
    prompt = MAIN_PROMPT.replace("{{id}}", item_id).replace("{{review_text}}", item["text"].strip())
    logger.debug(f"[Prompt] Built full prompt, length={len(prompt)}")
    raw = call_model(client, model, prompt)
    
    if not raw:
        logger.error(f"[Empty Response] id={item_id}, model returned empty string")
        return {"ok": False, "error": "empty_response", "raw": raw, "id": item_id}

    for attempt in range(max_retry + 1):
        logger.debug(f"[Validation] id={item_id}, attempt={attempt}, raw_len={len(raw)}")
        try:
            data = parse_json(raw)
            ok, reason = validate_item(data)
            if ok:
                logger.info(f"[Success] id={item_id}, urgency={data.get('urgency')}, intents={data.get('intents')}")
                return {"ok": True, "data": data}
            err = reason
            logger.warning(f"[Validation Failed] id={item_id}, reason={err}")
        except Exception as e:
            err = "invalid_json"
            logger.warning(f"[Parse Error] id={item_id}, error={str(e)}, raw_preview={raw[:100]}")

        if attempt < max_retry:
            logger.info(f"[Attempting Repair] id={item_id}, attempt={attempt + 1}/{max_retry}")
            # 2) 修复调用
            repair_prompt = REPAIR_PROMPT.replace("{{broken_output}}", raw[:300] if len(raw) > 300 else raw)
            raw = call_model(client, model, repair_prompt)
        else:
            logger.error(f"[Max Retries Exceeded] id={item_id}, error={err}, raw_output={raw[:100]}")

    return {"ok": False, "error": err, "raw": raw, "id": item_id}

def main():
    args = parse_args()

    # 配置日志
    log_file = f"process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("[STARTUP] Customer Service Comment Processor Started")
    logger.info("="*60)
    
    # 从环境变量读取
    import os
    try:
        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_BASE_URL") or os.environ["OPENAI_API_BASE"],
        )
        model = os.environ["MODEL_ID"]
        logger.info(f"[Config] model={model}, base_url={client.base_url}")
    except KeyError as e:
        logger.error(f"[Error] Missing environment variable: {str(e)}")
        return

    try:
        with open("comments.json", "r", encoding="utf-8") as f:
            items = json.load(f)
        logger.info(f"[Input] Loaded {len(items)} comments from comments.json")
    except FileNotFoundError:
        logger.error("[Error] comments.json not found")
        return
    except json.JSONDecodeError as e:
        logger.error(f"[Error] Failed to parse comments.json: {str(e)}")
        return

    try:
        start_index = build_start_index(items, args.start_id)
    except ValueError as e:
        logger.error(f"[Error] {str(e)}")
        return

    items_to_process = items[start_index:]
    if not items_to_process:
        logger.warning("[Skip] Nothing to process.")
        return

    logger.info(
        f"[Resume] start_id={args.start_id or items[0]['id']}, "
        f"start_index={start_index + 1}, process_count={len(items_to_process)}"
    )

    if args.overwrite:
        existing_results = []
        existing_failed = []
        logger.info("[Mode] overwrite=True, ignore existing results/failed files")
    else:
        existing_results = load_existing("results.json")
        existing_failed = load_existing("failed.json")
        logger.info(
            f"[Mode] resume merge enabled, existing_results={len(existing_results)}, "
            f"existing_failed={len(existing_failed)}"
        )

    results_by_id = {item["id"]: item for item in existing_results if "id" in item}
    failed_by_id = {item["id"]: item for item in existing_failed if "id" in item}
    run_success = 0
    run_failed = 0

    logger.info(f"[Processing] Starting processing of {len(items_to_process)} items...")
    start_time = time.time()

    for i, item in enumerate(items_to_process, 1):
        item_id = item.get("id")
        out = process_one(client, model, item)
        results_by_id.pop(item_id, None)
        failed_by_id.pop(item_id, None)

        if out["ok"]:
            results_by_id[item_id] = out["data"]
            run_success += 1
        else:
            failed_by_id[item_id] = out
            run_failed += 1

        if i % 5 == 0 or i == len(items_to_process):
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0.0
            logger.info(
                f"[Progress] {i}/{len(items_to_process)}, run_success={run_success}, "
                f"run_failed={run_failed}, rate={rate:.2f} items/sec"
            )
        time.sleep(args.sleep)

    results = ordered_by_comments(items, results_by_id)
    failed = ordered_by_comments(items, failed_by_id)

    elapsed = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info(
        f"[Summary] ThisRun={len(items_to_process)}, run_success={run_success}, "
        f"run_failed={run_failed}, merged_success={len(results)}, merged_failed={len(failed)}, Time={elapsed:.1f}s"
    )
    logger.info("="*60)

    try:
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"[Output] Saved {len(results)} successful results to results.json")
    except Exception as e:
        logger.error(f"[Error] Failed to write results.json: {str(e)}")

    try:
        with open("failed.json", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        logger.info(f"[Output] Saved {len(failed)} failed items to failed.json")
    except Exception as e:
        logger.error(f"[Error] Failed to write failed.json: {str(e)}")
    
    logger.info("[Completed] Processing finished. Check results.json and failed.json for details.")

if __name__ == "__main__":
    main()
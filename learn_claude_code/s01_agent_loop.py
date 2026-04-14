#!/usr/bin/env python3
# Harness: the loop -- keep feeding real tool results back into the model.
"""
s01_agent_loop.py - The Agent Loop
This file teaches the smallest useful coding-agent pattern:
    user message
      -> model reply
      -> if tool_use: execute tools
      -> write tool_result back to messages
      -> continue
It intentionally keeps the loop small, but still makes the loop state explicit
so later chapters can grow from the same structure.
"""
import os
import time
import argparse
import subprocess
from dataclasses import dataclass
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv(override=True)


def build_client() -> Anthropic:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")

    if not auth_token:
        raise RuntimeError(
            "Missing auth token. Please set ANTHROPIC_AUTH_TOKEN"
        )

    # Anthropic SDK 会自行拼接 /v1；若用户传入 .../v1 需要归一化避免 /v1/v1。
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]

    return Anthropic(auth_token=auth_token, base_url=base_url)


client = build_client()
MODEL = (
    os.getenv("ANTHROPIC_MODEL_ID")
    or os.getenv("MODEL_ID")
    or "claude-3-5-sonnet-latest"
)

if MODEL.lower().startswith("gpt-"):
    MODEL = "claude-3-5-sonnet-latest"
SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    "Use bash to inspect and change the workspace. Act first, then report clearly."
)
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command in the current workspace.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]
@dataclass
class LoopState:
    # The minimal loop state: history, loop count, and why we continue.
    messages: list
    turn_count: int = 1
    transition_reason: str | None = None
    debug: bool = False


def debug_log(state: LoopState, message: str) -> None:
    if state.debug:
        print(f"[debug][turn={state.turn_count}] {message}")


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(item in command for item in dangerous):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"
    output = (result.stdout + result.stderr).strip()
    return output[:50000] if output else "(no output)"
def extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    texts = []
    for block in content:
        text = None
        if isinstance(block, dict):
            text = block.get("text")
        else:
            text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts).strip()
def execute_tool_calls(response_content, state: LoopState) -> list[dict]:
    results = []
    for block in response_content:
        if block.type != "tool_use":
            continue
        command = block.input["command"]
        debug_log(state, f"tool_use id={block.id} command_len={len(command)}")
        print(f"\033[33m$ {command}\033[0m")
        output = run_bash(command)
        print(output[:200])
        debug_log(state, f"tool_result id={block.id} output_len={len(output)}")
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
    return results
def run_one_turn(state: LoopState) -> bool:
    start_ts = time.time()
    debug_log(state, f"request model={MODEL}")
    try:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=state.messages,
            tools=TOOLS,
            max_tokens=8000,
        )
    except Exception as exc:
        err_text = (
            f"Model call failed: {exc}\n"
            "Hint: verify ANTHROPIC_MODEL_ID is available on current gateway/account."
        )
        state.messages.append({"role": "assistant", "content": [{"type": "text", "text": err_text}]})
        state.transition_reason = None
        debug_log(state, f"request_failed latency={time.time() - start_ts:.2f}s")
        return False

    debug_log(
        state,
        f"response stop_reason={response.stop_reason} latency={time.time() - start_ts:.2f}s",
    )
    state.messages.append({"role": "assistant", "content": response.content})
    if response.stop_reason != "tool_use":
        state.transition_reason = None
        return False
    results = execute_tool_calls(response.content, state)
    if not results:
        state.transition_reason = None
        return False
    state.messages.append({"role": "user", "content": results})
    state.turn_count += 1
    state.transition_reason = "tool_result"
    return True
def agent_loop(state: LoopState) -> None:
    while run_one_turn(state):
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal Anthropic agent loop")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print per-turn debug logs (latency, stop_reason, tool calls)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Override model id for this run",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.model:
        MODEL = args.model

    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        state = LoopState(messages=history, debug=args.debug)
        agent_loop(state)
        final_text = extract_text(history[-1]["content"])
        if final_text:
            print(final_text)
        print()
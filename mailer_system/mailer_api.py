import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brand_prompt import VAHDAM_BRAND_SYSTEM_PROMPT

MODEL = "claude-sonnet-4-20250514"
API_URL = "https://api.anthropic.com/v1/messages"


def _strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end = len(lines) - 1
        text = "\n".join(lines[start:end]).strip()
    return text


def _call_api(brief_json, extra_instruction=""):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("[error] Set ANTHROPIC_API_KEY environment variable")

    user_content = (
        "Generate a complete Vahdam mailer for this brief. "
        "Use real numbers from the brief naturally in the copy. "
        "Return only valid JSON — no markdown fences no preamble."
    )
    if extra_instruction:
        user_content += f"\n\n{extra_instruction}"
    user_content += f"\n\nBRIEF:\n{brief_json}"

    payload = {
        "model": MODEL,
        "max_tokens": 4000,
        "system": VAHDAM_BRAND_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_content}
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_mailer(brief):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("[error] Set ANTHROPIC_API_KEY environment variable")

    brief_json = json.dumps(brief, indent=2)
    required_keys = {"subject_lines", "preheader", "sections", "cta_options", "performance_notes"}

    print(f"[api] Calling Claude API ({MODEL})...")
    t0 = time.time()

    data = _call_api(brief_json)
    raw = data["content"][0]["text"]
    raw = _strip_fences(raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if parsed is None or not required_keys.issubset(parsed.keys()):
        print("[api] Validation failed — retrying with strict instruction...")
        data = _call_api(
            brief_json,
            extra_instruction="IMPORTANT: Return ONLY a raw JSON object. No markdown. No explanation."
        )
        raw = data["content"][0]["text"]
        raw = _strip_fences(raw)
        parsed = json.loads(raw)

    elapsed = time.time() - t0
    usage = data.get("usage", {})
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)

    print(f"[api] Done — {in_tok} in / {out_tok} out / {elapsed:.1f}s")

    return {
        "response": parsed,
        "tokens_used": usage,
        "model": MODEL,
        "generated_at": datetime.now().isoformat(),
    }

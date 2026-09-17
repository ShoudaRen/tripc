"""
Provider-switchable LLM client.

- "OpenAI-compatible" covers OpenAI, DeepSeek, Moonshot, Qwen, local vLLM...
  (anything that speaks /chat/completions) - just change base URL + model.
- "Anthropic" speaks the /v1/messages API.
- "Demo mode" returns pre-generated outputs so the app can be fully
  demonstrated without any API key.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Callable

import httpx
from openai import OpenAI

PROVIDERS = [
    "Demo mode (no API key needed)",
    "Qwen (DashScope)",
    "DeepSeek",
    "OpenAI-compatible",
    "Anthropic",
]

DEFAULTS = {
    "Qwen (DashScope)": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                          "model": "qwen3.7-flash", "env_key": "DASHSCOPE_API_KEY"},
    "DeepSeek": {"base_url": "https://api.deepseek.com",
                 "model": "deepseek-v4-flash", "env_key": "DEEPSEEK_API_KEY"},
    "OpenAI-compatible": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
                          "env_key": "LLM_API_KEY"},
    "Anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-5",
                  "env_key": "ANTHROPIC_API_KEY"},
}


ENGINE_VERSION = "v2.5-streaming"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _post(url: str, headers: dict, payload: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:600]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} from server. Response body: {body}") from None


def test_connection(provider: str, base_url: str, api_key: str, model: str) -> str:
    try:
        generate(provider, base_url, api_key, model,
                 "Reply with the single word: pong", "ping")
        return "OK"
    except Exception as e:
        return explain_error(e)


def explain_error(error: Exception) -> str:
    """Turn common provider failures into safe, actionable UI messages."""
    message = str(error)
    if "AllocationQuota.FreeTierOnly" in message:
        return ("DashScope accepted the API key, but this model's free quota is exhausted and "
                'the account has "use free tier only" enabled. Choose qwen3.7-flash, add funds, '
                "or disable free-tier-only mode in the Model Studio console.")
    if "InvalidApiKey" in message or "invalid_api_key" in message or "HTTP 401" in message:
        return "The provider rejected the API key. Check that the key belongs to the Base URL region."
    if "model_not_found" in message or "InvalidParameter.Model" in message:
        return "The selected model is unavailable for this account or endpoint. Check the model name and region."
    return message


def _as_dict(value) -> dict:
    """Best-effort conversion for OpenAI/Anthropic usage objects."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            return dump(exclude_none=True)
        except TypeError:
            return dump()
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key, None))
    }


def _usage_summary(usage, *, input_chars: int, output_chars: int,
                   reasoning_chars: int, duration_seconds: float) -> dict:
    """Normalize provider usage while retaining useful local measurements."""
    raw = _as_dict(usage)
    details = _as_dict(
        raw.get("completion_tokens_details")
        or raw.get("output_tokens_details")
        or raw.get("output_token_details")
    )
    prompt_tokens = raw.get("prompt_tokens", raw.get("input_tokens"))
    completion_tokens = raw.get("completion_tokens", raw.get("output_tokens"))
    total_tokens = raw.get("total_tokens")
    if total_tokens is None and isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": details.get("reasoning_tokens"),
        "total_tokens": total_tokens,
        "input_chars": input_chars,
        "output_chars": output_chars,
        "reasoning_chars": reasoning_chars,
        "duration_seconds": round(duration_seconds, 2),
    }


def generate(provider: str, base_url: str, api_key: str, model: str,
             system: str, user: str, temperature: float = 0.3,
             thinking: bool = False,
             status_callback: Callable[[str], None] | None = None,
             usage_callback: Callable[[dict], None] | None = None) -> str:
    started = time.monotonic()
    if provider.startswith("Demo"):
        raise RuntimeError("Demo mode is handled by the app, not the LLM client.")
    base_url = (base_url or DEFAULTS.get(provider, {}).get("base_url", "")).rstrip("/")
    model = model or DEFAULTS.get(provider, {}).get("model", "")
    if not api_key:
        env_key = DEFAULTS.get(provider, {}).get("env_key", "the provider API key variable")
        raise RuntimeError(f"No API key was supplied. Enter one in the sidebar or set {env_key}.")
    if provider == "Anthropic":
        out = _post(f"{base_url}/v1/messages",
                    {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                    {"model": model, "max_tokens": 4096, "system": system,
                     "temperature": temperature,
                     "messages": [{"role": "user", "content": user}]})
        content = "".join(b.get("text", "") for b in out.get("content", []))
        if usage_callback:
            usage_callback(_usage_summary(
                out.get("usage"), input_chars=len(system) + len(user),
                output_chars=len(content), reasoning_chars=0,
                duration_seconds=time.monotonic() - started,
            ))
        return content
    # OpenAI-compatible (including Qwen/DashScope compatible mode).
    request = {
        "model": model,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if provider.startswith("Qwen"):
        request["extra_body"] = {"enable_thinking": thinking}
    elif provider == "DeepSeek":
        request["extra_body"] = {
            "thinking": {"type": "enabled" if thinking else "disabled"}
        }
        if thinking:
            request.pop("temperature", None)
            request["reasoning_effort"] = "high"
    # Do not inherit a configured-but-unreliable desktop proxy for provider calls.
    # This keeps long generations on the same direct route as the connection test.
    timeout = httpx.Timeout(600.0, connect=30.0, read=600.0, write=60.0, pool=30.0)
    with OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        http_client=httpx.Client(trust_env=False, timeout=timeout),
    ) as client:
        stream = client.chat.completions.create(**request)
        parts = []
        reasoning_chars = 0
        content_chars = 0
        final_usage = None
        last_status = 0.0
        for chunk in stream:
            if getattr(chunk, "usage", None) is not None:
                final_usage = chunk.usage
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None) or ""
            content = getattr(delta, "content", None) or ""
            reasoning_chars += len(reasoning)
            if content:
                parts.append(content)
                content_chars += len(content)
            now = time.monotonic()
            if status_callback and now - last_status >= 0.5:
                phase = (f"receiving final answer · {content_chars} chars"
                         if content_chars else
                         f"thinking stream active · {reasoning_chars} chars received"
                         if reasoning_chars else "stream connected · waiting for first chunk")
                try:
                    status_callback(phase)
                except Exception:
                    pass
                last_status = now
    content = "".join(parts)
    if not content:
        detail = (f" The stream contained {reasoning_chars} hidden reasoning characters but no "
                  "final content." if reasoning_chars else "")
        raise RuntimeError("The model stream ended without final content." + detail)
    if status_callback:
        try:
            status_callback(f"response received · {content_chars} final chars")
        except Exception:
            pass
    if usage_callback:
        try:
            usage_callback(_usage_summary(
                final_usage, input_chars=len(system) + len(user),
                output_chars=content_chars, reasoning_chars=reasoning_chars,
                duration_seconds=time.monotonic() - started,
            ))
        except Exception:
            pass
    return content

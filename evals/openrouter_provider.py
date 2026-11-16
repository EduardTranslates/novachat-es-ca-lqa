"""
openrouter_provider.py - Promptfoo provider that calls OpenRouter (OpenAI-compatible
chat completions), so the same eval set can run on models from other vendors.

Same interface as gemini_provider.py: call_api(prompt, options, context).

API key: read from the OPENROUTER_API_KEY environment variable and sent as
"Authorization: Bearer <key>". If the variable is not set, the request is sent
without a key (useful when a proxy injects authentication). Never hardcode the key.

Config (promptfooconfig.yaml):
    model:        OpenRouter model id, e.g. openai/gpt-4o-mini
    temperature:  sampling temperature (default 0)
    response_format_json: optional, true to request a JSON object
    max_tokens:   optional output cap
    max_retries:  retries on HTTP 429/500/502/503/504 (default 2)
"""

import json
import os
import time

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _to_messages(prompt):
    """Promptfoo chat prompts are a JSON list of role/content; plain text becomes one user turn."""
    try:
        messages = json.loads(prompt)
        if isinstance(messages, list):
            return messages
    except json.JSONDecodeError:
        pass
    return [{"role": "user", "content": prompt}]


def call_api(prompt, options, context):
    config = options.get("config", {})
    body = {
        "model": config.get("model", "openai/gpt-4o-mini"),
        "messages": _to_messages(prompt),
        "temperature": config.get("temperature", 0),
    }
    if config.get("max_tokens"):
        body["max_tokens"] = config["max_tokens"]
    if config.get("response_format_json"):
        body["response_format"] = {"type": "json_object"}

    headers = {"Content-Type": "application/json", "X-Title": "NovaChat ES/CA eval set"}
    if os.environ.get("OPENROUTER_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['OPENROUTER_API_KEY']}"

    retries = config.get("max_retries", 2)
    for attempt in range(retries + 1):
        started = time.time()
        try:
            response = requests.post(API_URL, json=body, headers=headers, timeout=150)
        except requests.RequestException as err:
            return {"error": f"Network error: {err}"}
        if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(10 * (attempt + 1))
            continue
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text[:300]}"}
        data = response.json()
        break

    if "error" in data:
        return {"error": f"API error: {json.dumps(data['error'])[:300]}"}
    choices = data.get("choices", [])
    if not choices:
        return {"error": f"No choices returned: {json.dumps(data)[:300]}"}
    text = choices[0].get("message", {}).get("content") or ""

    usage = data.get("usage", {})
    return {
        "output": text,
        "latencyMs": int((time.time() - started) * 1000),
        "tokenUsage": {
            "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0),
        },
    }

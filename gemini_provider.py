"""
gemini_provider.py - Promptfoo provider that calls the Gemini API (generateContent).

Written in plain Python with `requests` (pip install requests) instead of using
Promptfoo's built-in Google provider, so that every step of the request is
visible and easy to adapt to another API. `requests` rather than the standard
library's urllib because urllib cannot tunnel through HTTPS proxies, which
corporate networks and secret-injecting proxies often use.

API key: read from the GEMINI_API_KEY environment variable and sent in the
x-goog-api-key header. If the variable is not set, the request is sent without
a key (useful when a proxy injects authentication). Never hardcode the key.

Config (promptfooconfig.yaml):
    model:        Gemini model id, e.g. gemini-3.8-flash
    temperature:  sampling temperature (default 0)
    thinking_level: optional Gemini 3 thinking level, e.g. low or high
    response_mime_type: optional, e.g. application/json to force JSON output
    max_retries:  retries on HTTP 429/500/502/503/504 (default 2)
"""

import json
import os
import time

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _to_gemini(prompt):
    """Convert a Promptfoo chat prompt (JSON list of role/content) to Gemini format."""
    try:
        messages = json.loads(prompt)
    except json.JSONDecodeError:
        messages = [{"role": "user", "content": prompt}]

    system = [m["content"] for m in messages if m["role"] == "system"]
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in messages if m["role"] != "system"
    ]
    body = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system)}]}
    return body


def call_api(prompt, options, context):
    config = options.get("config", {})
    model = config.get("model", "gemini-3.8-flash")
    body = _to_gemini(prompt)
    body["generationConfig"] = {"temperature": config.get("temperature", 0)}
    if config.get("thinking_level"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": config["thinking_level"]}
    if config.get("response_mime_type"):
        body["generationConfig"]["responseMimeType"] = config["response_mime_type"]

    headers = {"Content-Type": "application/json"}
    if os.environ.get("GEMINI_API_KEY"):
        headers["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]

    url = API_URL.format(model=model)
    retries = config.get("max_retries", 2)
    for attempt in range(retries + 1):
        started = time.time()
        try:
            response = requests.post(url, json=body, headers=headers, timeout=150)
        except requests.RequestException as err:
            return {"error": f"Network error: {err}"}
        if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(10 * (attempt + 1))  # free tier: back off on rate limits
            continue
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text[:300]}"}
        data = response.json()
        break

    candidates = data.get("candidates", [])
    if not candidates:
        return {"error": f"No candidates returned: {json.dumps(data)[:300]}"}
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))

    usage = data.get("usageMetadata", {})
    return {
        "output": text,
        "latencyMs": int((time.time() - started) * 1000),
        "tokenUsage": {
            "prompt": usage.get("promptTokenCount", 0),
            "completion": usage.get("candidatesTokenCount", 0),
            "total": usage.get("totalTokenCount", 0),
        },
    }

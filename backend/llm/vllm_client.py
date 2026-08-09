# backend/llm/vllm_client.py
import os
import json
import requests

MODEL_API_URL = os.getenv("MODEL_API_URL", "http://127.0.0.1:8000")
LLM_MODEL = os.getenv("LLM_MODEL", "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4")

DEFAULT_TIMEOUT = 180  # seconds


def generate(prompt: str) -> str:
    """Single-shot non-streaming completion using OpenAI-compatible vLLM API."""
    try:
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful technical support agent.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
            "stream": False,
        }

        url = f"{MODEL_API_URL}/v1/chat/completions"
        r = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()

        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return text or ""

    except Exception as e:
        print(f"[VLLM ERROR] Non-stream call failed: {e}")
        return ""


def generate_stream(prompt: str):
    """Streaming chat completion from vLLM."""
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful technical support agent."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
        "stream": True,
    }

    url = f"{MODEL_API_URL}/v1/chat/completions"

    try:
        with requests.post(
            url, json=payload, stream=True, timeout=DEFAULT_TIMEOUT
        ) as r:
            r.raise_for_status()

            for raw in r.iter_lines():
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw.decode("utf-8", errors="ignore"))
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue

    except Exception as e:
        print(f"[VLLM ERROR] Stream call failed: {e}")
        yield ""  # prevent UI breaking

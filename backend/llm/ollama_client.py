# backend/llm/ollama_client.py
import os
import json
import requests

MODEL_API_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:70b")


def generate(prompt: str) -> str:
    payload = {"model": LLM_MODEL, "prompt": prompt, "stream": False}
    r = requests.post(f"{MODEL_API_URL}/api/generate", json=payload)
    r.raise_for_status()
    return r.json().get("response", "")


def generate_stream(prompt: str):
    payload = {"model": LLM_MODEL, "prompt": prompt, "stream": True}
    r = requests.post(f"{MODEL_API_URL}/api/generate", json=payload, stream=True)
    r.raise_for_status()
    for raw in r.iter_lines():
        if not raw:
            continue
        try:
            chunk = json.loads(raw.decode())
            if "response" in chunk:
                yield chunk["response"]
        except Exception:
            continue

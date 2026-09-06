# backend/llm/llm.py
"""
Universal LLM Interface supporting NVIDIA NIM, Groq, and Local Ollama.
Allows zero-code switching between hosted high-throughput inference (Groq/NVIDIA)
and local offline deployment (Ollama on GPU/CPU), with automated multi-tier failover.
"""

import os
import re
import time
import asyncio
import logging
from typing import List, Optional, Dict
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
logger = logging.getLogger(__name__)

# Temporary model cooldown tracker to skip rate-limited models instantly
_MODEL_COOLDOWNS: Dict[str, float] = {}
COOLDOWN_DURATION_SEC = 60.0  # 1 minute

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "OLLAMA").upper()

# Resolve Provider Defaults
DEFAULT_ENDPOINTS = {
    "OLLAMA": "http://localhost:11434",
    "GROQ": "https://api.groq.com/openai/v1",
    "NVIDIA": "https://integrate.api.nvidia.com/v1",
    "OPENAI": "https://api.openai.com/v1",
}

DEFAULT_MODELS = {
    "OLLAMA": "llama3.1",
    "GROQ": "qwen/qwen3.8-27b",
    "NVIDIA": "meta/llama-3.2-11b-vision-instruct",
    "OPENAI": "gpt-4o-mini",
}

FALLBACK_MODELS = {
    "GROQ": ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"],
    "NVIDIA": ["nvidia/nemotron-3-super-120b-a12b", "openai/gpt-oss-20b"],
    "OLLAMA": ["llama3.1"]
}

# Resolve API URL
raw_api_url = os.getenv("MODEL_API_URL")
if not raw_api_url:
    raw_api_url = DEFAULT_ENDPOINTS.get(MODEL_PROVIDER, "http://localhost:11434")

# Normalize base_url
if MODEL_PROVIDER == "OLLAMA":
    MODEL_API_URL = raw_api_url.rstrip("/")
else:
    clean_url = raw_api_url.rstrip("/")
    MODEL_API_URL = clean_url if clean_url.endswith("/v1") else f"{clean_url}/v1"

# Resolve Model Name
LLM_MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(MODEL_PROVIDER, "llama3.1")

# Resolve API Key based on provider
if MODEL_PROVIDER == "GROQ":
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"
elif MODEL_PROVIDER == "NVIDIA":
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"
elif MODEL_PROVIDER == "OPENAI":
    api_key = os.getenv("OPENAI_API_KEY") or "EMPTY"
else:
    api_key = "ollama"

if MODEL_PROVIDER == "OLLAMA":
    client = AsyncOpenAI(api_key="ollama", base_url=MODEL_API_URL, timeout=120.0, max_retries=0)
else:
    client = AsyncOpenAI(api_key=api_key, base_url=MODEL_API_URL, timeout=60.0, max_retries=0)

logger.info(f"⚡ LLM Provider Initialized: {MODEL_PROVIDER} | URL: {MODEL_API_URL} | Model: {LLM_MODEL}")


def _get_candidate_models() -> List[str]:
    """Returns candidate models ordered with active (non-cooldown) models first."""
    all_models = [LLM_MODEL]
    for alt in FALLBACK_MODELS.get(MODEL_PROVIDER, []):
        if alt not in all_models:
            all_models.append(alt)

    now = time.time()
    active = [m for m in all_models if _MODEL_COOLDOWNS.get(m, 0) < now]
    in_cooldown = [m for m in all_models if _MODEL_COOLDOWNS.get(m, 0) >= now]
    return active + in_cooldown

def _mark_model_cooldown(model_name: str):
    """Marks a model as in cooldown due to rate limits."""
    _MODEL_COOLDOWNS[model_name] = time.time() + COOLDOWN_DURATION_SEC
    logger.info(f"⏳ Placed model {model_name} in cooldown for {COOLDOWN_DURATION_SEC}s.")


# -----------------------------------------------
# ASYNC Call with Automatic Resilient Failover
# -----------------------------------------------
async def call_model_async(prompt: str, max_tokens: int = 768, max_retries_per_model: int = 3) -> str:
    """
    Asynchronous inference call with automatic retries and model failover.
    """
    models_to_try = _get_candidate_models()
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        for attempt in range(max_retries_per_model):
            try:
                kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": max_tokens,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                }
                if MODEL_PROVIDER == "GROQ":
                    kwargs["extra_body"] = {"reasoning_format": "hidden"}
                res = await client.chat.completions.create(**kwargs)
                content = res.choices[0].message.content or ""
                # Strip thinking artifacts if returned by reasoning models
                if "<think>" in content and "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                elif "<think>" in content:
                    content = content.split("<think>")[-1].strip()
                if content.strip():
                    return content.strip()
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "TPD" in err_str or "tokens per day" in err_str.lower():
                    logger.warning(f"Daily limit (TPD) on model {model_name}: {e}. Placing in cooldown.")
                    _mark_model_cooldown(model_name)
                    break
                elif "429" in err_str or "rate limit" in err_str.lower() or "tpm" in err_str.lower() or "otpm" in err_str.lower():
                    # Parse wait time if available in error message (e.g., "try again in 2.34s")
                    wait_sec = 2.0 * (attempt + 1)
                    match = re.search(r"try again in (\d+(\.\d+)?)s", err_str.lower())
                    if match:
                        try:
                            wait_sec = float(match.group(1)) + 0.5
                        except Exception:
                            pass
                    logger.warning(f"Rate limit on model {model_name} (attempt {attempt+1}): {e}. Waiting {wait_sec:.1f}s...")
                    await asyncio.sleep(wait_sec)
                    continue
                logger.warning(f"Error on model {model_name} (attempt {attempt+1}): {e}")
                await asyncio.sleep(1.0)

    # Final safety attempt if all candidate runs failed
    if last_error:
        logger.warning("Attempting final recovery across fallback models after cooldown reset...")
        for model_name in FALLBACK_MODELS.get(MODEL_PROVIDER, [LLM_MODEL]):
            try:
                await asyncio.sleep(2.0)
                kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": max_tokens
                }
                if MODEL_PROVIDER == "GROQ":
                    kwargs["extra_body"] = {"reasoning_format": "hidden"}
                res = await client.chat.completions.create(**kwargs)
                content = res.choices[0].message.content or ""
                if "<think>" in content and "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                elif "<think>" in content:
                    content = content.split("<think>")[-1].strip()
                if content.strip():
                    return content.strip()
            except Exception:
                continue

        logger.error(f"All model attempts exhausted. Last error: {last_error}")
        raise last_error
    return ""


# -----------------------------------------------
# ASYNC Stream with Automatic Model Failover
# -----------------------------------------------
async def call_model_stream(prompt: str, max_tokens: int = 768):
    """
    Asynchronous streaming generator with model failover on start.
    """
    models_to_try = _get_candidate_models()

    for model_name in models_to_try:
        try:
            kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stream": True
            }
            if MODEL_PROVIDER == "GROQ":
                kwargs["extra_body"] = {"reasoning_format": "hidden"}
            stream = await client.chat.completions.create(**kwargs)
            in_think = False
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                if "<think>" in delta:
                    in_think = True
                    continue
                if "</think>" in delta:
                    in_think = False
                    continue
                if not in_think:
                    yield delta
            return
        except Exception as e:
            err_str = str(e)
            if "TPD" in err_str or "tokens per day" in err_str.lower():
                _mark_model_cooldown(model_name)
            elif "429" in err_str or "rate limit" in err_str.lower():
                await asyncio.sleep(2.0)
            logger.warning(f"Stream error on model {model_name}: {e}. Trying next model...")
            await asyncio.sleep(0.5)
            continue


# -----------------------------------------------
# SYNC Call
# -----------------------------------------------
def call_model_sync(prompt: str, max_tokens: int = 768) -> str:
    """Synchronous completion wrapper for evaluation or offline pipelines."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(call_model_async(prompt, max_tokens=max_tokens))

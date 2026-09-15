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
COOLDOWN_DURATION_SEC = float(os.getenv("LLM_COOLDOWN_SEC", "60"))  # rate-limit cooldown

# Groq model cache to avoid hitting API on every request
_GROQ_MODELS_CACHE: List[str] = []
_GROQ_MODELS_CACHE_TIMESTAMP: float = 0
_GROQ_MODELS_CACHE_TTL = float(os.getenv("GROQ_MODELS_CACHE_TTL", "21600"))  # 6 hours in seconds

# Fallback hardcoded Groq model list (used if API fails or cache is stale and refresh fails)
GROQ_MODEL_FALLBACK = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
]

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "OLLAMA").upper()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
NVIDIA_NIM_API_BASE = os.getenv("NVIDIA_NIM_API_BASE", "https://integrate.api.nvidia.com/v1")

# Provider-specific model lists (can be overridden by env)
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", "llama3.1:8b,llama3:8b,phi3:mini").split(",")
GROQ_MODEL_PRIORITY_ENV = os.getenv("GROQ_MODEL_PRIORITY")  # comma-separated override
NVIDIA_MODELS = os.getenv("NVIDIA_MODELS", "nemotron-3-8b-instruct,nemotron-3-22b-instruct")

# Initialize provider-specific clients
groq_client: Optional[AsyncOpenAI] = None
nim_client: Optional[AsyncOpenAI] = None
ollama_client: Optional[AsyncOpenAI] = None

if GROQ_API_KEY:
    groq_client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_API_BASE,
    )

if NVIDIA_NIM_API_KEY:
    nim_client = AsyncOpenAI(
        api_key=NVIDIA_NIM_API_KEY,
        base_url=NVIDIA_NIM_API_BASE,
    )

if OLLAMA_BASE_URL:
    ollama_client = AsyncOpenAI(
        api_key="ollama",  # Ollama doesn't check the key
        base_url=f"{OLLAMA_BASE_URL}/v1",
    )

# Embedding model (shared across providers)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")
EMBEDDING_MODEL = None  # lazy-loaded on first use

LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))

# Track consecutive failures per model to avoid hammering a dead model
_model_failure_counts: Dict[str, int] = {}
_FAILURE_THRESHOLD = 3  # Skip model after 3 consecutive failures


def _mark_model_cooldown(model_name: str) -> None:
    """Mark a model as temporarily unavailable due to rate limit or error."""
    _MODEL_COOLDOWNS[model_name] = time.time() + COOLDOWN_DURATION_SEC
    logger.warning(f"Model {model_name} on cooldown until {_MODEL_COOLDOWNS[model_name]}")


def _is_model_on_cooldown(model_name: str) -> bool:
    """Check if a model is currently in cooldown."""
    cooldown_until = _MODEL_COOLDOWNS.get(model_name, 0)
    return time.time() < cooldown_until


def _record_model_failure(model_name: str) -> None:
    """Increment failure count for a model."""
    _model_failure_counts[model_name] = _model_failure_counts.get(model_name, 0) + 1
    if _model_failure_counts[model_name] >= _FAILURE_THRESHOLD:
        _mark_model_cooldown(model_name)
        logger.warning(
            f"Model {model_name} failed {_model_failure_counts[model_name]} times, "
            f"placing on cooldown for {COOLDOWN_DURATION_SEC} seconds"
        )


def _reset_model_failure_count(model_name: str) -> None:
    """Reset failure count for a model on success."""
    if model_name in _model_failure_counts:
        del _model_failure_counts[model_name]


async def _fetch_groq_models() -> List[str]:
    """Fetch available model IDs from Groq API."""
    if not groq_client:
        logger.warning("Groq client not initialized, cannot fetch models")
        return []

    try:
        logger.info("Fetching available models from Groq API")
        models_response = await groq_client.models.list()
        model_ids = [model.id for model in models_response.data]
        logger.info(f"Fetched {len(model_ids)} models from Groq: {model_ids}")
        return model_ids
    except Exception as e:
        logger.error(f"Failed to fetch Groq models: {e}")
        return []


def get_groq_model_priority() -> List[str]:
    """
    Get Groq model priority list, using cache if fresh, otherwise attempting to refresh.
    Falls back to hardcoded list if API call fails.
    """
    global _GROQ_MODELS_CACHE, _GROQ_MODELS_CACHE_TIMESTAMP

    # If we have an explicit override via env, use it
    if GROQ_MODEL_PRIORITY_ENV:
        return [m.strip() for m in GROQ_MODEL_PRIORITY_ENV.split(",") if m.strip()]

    # Check if cache is fresh
    now = time.time()
    if _GROQ_MODELS_CACHE and (now - _GROQ_MODELS_CACHE_TIMESTAMP) < _GROQ_MODELS_CACHE_TTL:
        logger.debug(f"Using cached Groq models ({len(_GROQ_MODELS_CACHE)} models)")
        return _GROQ_MODELS_CACHE.copy()

    # Cache is stale or empty, try to refresh
    logger.info("Refreshing Groq model cache")
    try:
        # Run the async fetch in a sync context (we're called from async functions, but we can't await here directly)
        # Since this is called from within async functions, we need to handle it differently.
        # We'll store the coroutine and let the caller handle it, or we can use asyncio.run if we're in a thread.
        # However, to avoid complexity, we'll return the cache if available, else fallback, and let the async
        # refresh happen in the background via a separate mechanism.
        # For simplicity in this context, we'll do a blocking call if we're already in an event loop.
        # But note: we cannot block the event loop. Instead, we'll return the cache if we have any,
        # otherwise fallback, and log that we're trying to refresh in the background.
        # We'll implement a background refresh by setting a flag and letting the next call use the updated cache.
        # Given the complexity, and since we are in a function that might be called from async context,
        # we will return the current cache (even if stale) and note that a refresh is needed.
        # We'll trigger an async refresh in the background by creating a task.
        # However, we cannot create a task from a non-async context easily.
        # So we'll do: if we have no cache, we return fallback and log that we're trying to fetch.
        # If we have cache (even stale), we return it and log that we're refreshing in background.
        # We'll use a simple approach: if cache is stale, we attempt to fetch synchronously but with a timeout.
        # This is acceptable because the model list doesn't change frequently and we are willing to block
        # briefly for a more accurate list.
        # We'll use asyncio.run if there's no running loop, or we'll run the coroutine and block until done.
        # This is safe because the model list fetch is infrequent.
        try:
            # Try to get the running loop
            loop = asyncio.get_running_loop()
            # We are in a running loop, we cannot block it. Instead, we'll schedule the fetch and use cache for now.
            # We'll create a task to update the cache in the background.
            async def _update_cache():
                global _GROQ_MODELS_CACHE, _GROQ_MODELS_CACHE_TIMESTAMP
                models = await _fetch_groq_models()
                if models:
                    _GROQ_MODELS_CACHE = models
                    _GROQ_MODELS_CACHE_TIMESTAMP = time.time()
                    logger.info(f"Background updated Groq model cache with {len(models)} models")
                else:
                    logger.warning("Background Groq model fetch failed, keeping existing cache")

            # Schedule the background update
            loop.create_task(_update_cache())
            logger.info("Scheduled background Groq model cache update")
        except RuntimeError:
            # No running loop, we can use asyncio.run
            models = asyncio.run(_fetch_groq_models())
            if models:
                _GROQ_MODELS_CACHE = models
                _GROQ_MODELS_CACHE_TIMESTAMP = time.time()
                logger.info(f"Fetched and cached {len(models)} Groq models")
            else:
                logger.warning("Failed to fetch Groq models, keeping existing cache if any")

    except Exception as e:
        logger.error(f"Error during Groq model cache refresh: {e}")

    # Return cache if we have any, otherwise fallback
    if _GROQ_MODELS_CACHE:
        logger.debug(f"Returning Groq model cache ({len(_GROQ_MODELS_CACHE)} models)")
        return _GROQ_MODELS_CACHE.copy()
    else:
        logger.warning("Using fallback Groq model list")
        return GROQ_MODEL_FALLBACK.copy()


def _get_fallback_models() -> List[str]:
    """Get fallback models for the current provider."""
    if MODEL_PROVIDER == "GROQ":
        return GROQ_MODEL_FALLBACK.copy()
    elif MODEL_PROVIDER == "NVIDIA":
        return NVIDIA_MODELS.split(",")
    elif MODEL_PROVIDER == "OLLAMA":
        return OLLAMA_MODELS
    else:
        return []


def _get_model_provider_client(provider: str) -> Optional[AsyncOpenAI]:
    """Get the initialized client for a provider."""
    if provider == "GROQ":
        return groq_client
    elif provider == "NVIDIA":
        return nim_client
    elif provider == "OLLAMA":
        return ollama_client
    return None


async def call_model_async(
    prompt: str,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
    top_p: float = LLM_TOP_P,
) -> str:
    """
    Asynchronous inference call with automatic retries and model failover.
    Tries models in priority order, skipping rate-limited or repeatedly failing models.
    """
    last_error: Optional[Exception] = None
    tried_models = set()

    # Get the provider-specific model priority
    if MODEL_PROVIDER == "GROQ":
        model_priority = get_groq_model_priority()
    elif MODEL_PROVIDER == "NVIDIA":
        model_priority = NVIDIA_MODELS.split(",")
    elif MODEL_PROVIDER == "OLLAMA":
        model_priority = OLLAMA_MODELS
    else:
        model_priority = []

    client = _get_model_provider_client(MODEL_PROVIDER)
    if not client:
        error_msg = f"No client initialized for provider {MODEL_PROVIDER}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(
        f"Starting LLM call with provider {MODEL_PROVIDER}, trying models in order: {model_priority}"
    )

    for model_name in model_priority:
        # Skip if we've already tried this model in this call (avoid loops)
        if model_name in tried_models:
            continue
        tried_models.add(model_name)

        # Skip if model is on cooldown
        if _is_model_on_cooldown(model_name):
            logger.debug(f"Skipping {model_name} (on cooldown)")
            continue

        try:
            logger.debug(f"Attempting model {model_name}")
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
            )
            answer = completion.choices[0].message.content
            if answer is None:
                raise ValueError("Empty response from model")

            # Reset failure count on success
            _reset_model_failure_count(model_name)
            logger.info(f"Successfully used model {model_name}")
            return answer.strip()

        except Exception as e:
            last_error = e
            err_str = str(e)
            logger.warning(f"Error on model {model_name} (attempt): {e}")

            # Check for specific error types that should trigger cooldown or model skip
            if "TPD" in err_str or "tokens per day" in err_str.lower():
                _mark_model_cooldown(model_name)
                logger.warning(f"Model {model_name} marked cooldown due to TPD limit")
            elif "429" in err_str or "rate limit" in err_str.lower():
                # Rate limit - wait briefly then try next model (cooldown will be set by _mark_model_cooldown if we had TPD)
                # For pure rate limit without TPD, we'll still mark cooldown to avoid hammering
                _mark_model_cooldown(model_name)
                await asyncio.sleep(2.0)  # Brief wait before next model
            elif "400" in err_str and ("model" in err_str.lower() or "not found" in err_str.lower()):
                # Model not found or invalid model - this is important for our dynamic model list
                # We should refresh the model list and try again with the updated list
                logger.warning(f"Model {model_name} not found (400), will refresh Groq model list")
                # Force refresh of Groq model cache on next call
                global _GROQ_MODELS_CACHE_TIMESTAMP
                _GROQ_MODELS_CACHE_TIMESTAMP = 0  # Invalidate cache
                # Mark this model as failed so we don't try it again in this call
                _record_model_failure(model_name)
                # If we are using Groq and we got a 400, we should break and retry with updated list
                if MODEL_PROVIDER == "GROQ":
                    logger.info("Breaking current model list iteration to refresh and retry with updated models")
                    break  # Break out of the for loop to retry with updated model list
            else:
                # Other errors - increment failure count
                _record_model_failure(model_name)

            # Wait briefly before trying next model to avoid hammering
            await asyncio.sleep(0.5)

    # If we broke out of the loop due to a 400 (model not found) and we are using Groq,
    # we should retry the entire process with an updated model list.
    if MODEL_PROVIDER == "GROQ" and last_error and "400" in str(last_error) and "model" in str(last_error).lower():
        logger.info("Retrying LLM call with refreshed Groq model list after 400 error")
        # Clear the tried models set so we can try the updated list
        tried_models.clear()
        # Invalidate the Groq model cache to force refresh
        global _GROQ_MODELS_CACHE_TIMESTAMP
        _GROQ_MODELS_CACHE_TIMESTAMP = 0
        # Get updated model priority
        model_priority = get_groq_model_priority()
        logger.info(f"Retrying with updated model list: {model_priority}")

        for model_name in model_priority:
            if model_name in tried_models:
                continue
            tried_models.add(model_name)

            if _is_model_on_cooldown(model_name):
                logger.debug(f"Skipping {model_name} (on cooldown) in retry")
                continue

            try:
                logger.debug(f"Retry attempt with model {model_name}")
                completion = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=False,
                )
                answer = completion.choices[0].message.content
                if answer is None:
                    raise ValueError("Empty response from model")

                _reset_model_failure_count(model_name)
                logger.info(f"Successfully used model {model_name} on retry")
                return answer.strip()

            except Exception as e:
                last_error = e
                err_str = str(e)
                logger.warning(f"Error on retry model {model_name}: {e}")
                if "TPD" in err_str or "tokens per day" in err_str.lower():
                    _mark_model_cooldown(model_name)
                elif "429" in err_str or "rate limit" in err_str.lower():
                    _mark_model_cooldown(model_name)
                    await asyncio.sleep(2.0)
                elif "400" in err_str and ("model" in err_str.lower() or "not found" in err_str.lower()):
                    _record_model_failure(model_name)
                    # Continue to next model in retry list
                else:
                    _record_model_failure(model_name)
                await asyncio.sleep(0.5)

    # If we get here, all models failed
    logger.error(f"All model attempts exhausted. Last error: {last_error}")
    raise last_error


# ASYNC Stream with Automatic Model Failover
async def call_model_async_stream(
    prompt: str,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
    top_p: float = LLM_TOP_P,
):
    """
    Asynchronous streaming generator with model failover on start.
    Note: If failover occurs mid-stream, the stream will be restarted from the beginning
    with the new model (this is a limitation of the current approach).
    """
    # Get the provider-specific model priority
    if MODEL_PROVIDER == "GROQ":
        model_priority = get_groq_model_priority()
    elif MODEL_PROVIDER == "NVIDIA":
        model_priority = NVIDIA_MODELS.split(",")
    elif MODEL_PROVIDER == "OLLAMA":
        model_priority = OLLAMA_MODELS
    else:
        model_priority = []

    client = _get_model_provider_client(MODEL_PROVIDER)
    if not client:
        error_msg = f"No client initialized for provider {MODEL_PROVIDER}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(
        f"Starting LLM stream with provider {MODEL_PROVIDER}, trying models in order: {model_priority}"
    )

    for model_name in model_priority:
        # Skip if model is on cooldown
        if _is_model_on_cooldown(model_name):
            logger.debug(f"Skipping {model_name} (on cooldown)")
            continue

        try:
            logger.debug(f"Attempting stream with model {model_name}")
            stream = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )

            # Reset failure count for this model as we're about to use it successfully
            _reset_model_failure_count(model_name)
            logger.info(f"Successfully opened stream with model {model_name}")

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

            # If we successfully finished the stream, return
            return

        except Exception as e:
            logger.warning(f"Stream error on model {model_name}: {e}. Trying next model...")
            if "TPD" in str(e) or "tokens per day" in str(e).lower():
                _mark_model_cooldown(model_name)
            elif "429" in str(e) or "rate limit" in str(e).lower():
                _mark_model_cooldown(model_name)
                await asyncio.sleep(2.0)
            elif "400" in str(e) and ("model" in str(e).lower() or "not found" in str(e).lower()):
                _record_model_failure(model_name)
                # Force refresh Groq model list for next attempt
                global _GROQ_MODELS_CACHE_TIMESTAMP
                _GROQ_MODELS_CACHE_TIMESTAMP = 0
            else:
                _record_model_failure(model_name)
            await asyncio.sleep(0.5)
            continue

    # If we get here, all models failed to start a stream
    logger.error(f"All model attempts exhausted for streaming")
    raise RuntimeError("Failed to initialize LLM stream with any model")


# -----------------------------------------------
# SYNC Call
# -----------------------------------------------
def call_model_sync(prompt: str, max_tokens: int = LLM_MAX_TOKENS) -> str:
    """Synchronous completion wrapper for evaluation or offline pipelines."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(call_model_async(prompt, max_tokens=max_tokens))
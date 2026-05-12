# backend/llm/llm.py
import os
import asyncio
import logging

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

logging.basicConfig(level=logging.INFO)

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "OLLAMA").upper()
MODEL_API_URL  = os.getenv("MODEL_API_URL", "http://localhost:11434")
LLM_MODEL      = os.getenv("LLM_MODEL", "gemma4:e4b")

logging.info(f"LLM Provider : {MODEL_PROVIDER}")
logging.info(f"API URL      : {MODEL_API_URL}")
logging.info(f"Model        : {LLM_MODEL}")

# -----------------------------------------------
# LangChain LLM Wrapper
# -----------------------------------------------
if MODEL_PROVIDER == "OLLAMA":
    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=MODEL_API_URL,
        temperature=0.15,
    )
else:
    # vLLM / OpenAI-compatible endpoint
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=os.getenv("OPENAI_API_KEY", "EMPTY"),
        base_url=f"{MODEL_API_URL}/v1",
        temperature=0.15,
        max_tokens=None,
    )


# -----------------------------------------------
# SYNC Call
# -----------------------------------------------
def call_model_sync(prompt: str) -> str:
    logging.info("[LLM] Sync inference")
    res = llm.invoke(prompt)
    return res.content


# -----------------------------------------------
# ASYNC Call
# -----------------------------------------------
async def call_model_async(prompt: str) -> str:
    return await asyncio.to_thread(call_model_sync, prompt)

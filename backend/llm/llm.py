# backend/llm/llm.py
import os
import asyncio
import logging

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO)

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "OLLAMA").upper()
MODEL_API_URL  = os.getenv("MODEL_API_URL", "http://localhost:11434")
LLM_MODEL      = os.getenv("LLM_MODEL", "llama3.1")

logging.info(f"LLM Provider : {MODEL_PROVIDER}")
logging.info(f"API URL      : {MODEL_API_URL}")
logging.info(f"Model        : {LLM_MODEL}")

from openai import AsyncOpenAI

# -----------------------------------------------
# Native OpenAI Client
# -----------------------------------------------
api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
if MODEL_PROVIDER == "OLLAMA":
    client = AsyncOpenAI(api_key="ollama", base_url=MODEL_API_URL)
else:
    client = AsyncOpenAI(api_key=api_key, base_url=f"{MODEL_API_URL}/v1")

# We no longer export llm, we export client and LLM_MODEL


# -----------------------------------------------
# SYNC Call
# -----------------------------------------------
def call_model_sync(prompt: str) -> str:
    logging.info("[LLM] Sync inference")
    res = asyncio.run(client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    ))
    return res.choices[0].message.content


# -----------------------------------------------
# ASYNC Call
# -----------------------------------------------
async def call_model_async(prompt: str) -> str:
    res = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return res.choices[0].message.content

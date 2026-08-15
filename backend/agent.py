# backend/agent.py
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Iterable
import urllib.parse

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory

from .vectorstore import get_retriever
from .llm.llm import llm
from .chat_store import save_message
from .db import REDIS_URL, SESSION_TTL
from .vectorstore import get_retriever
from .tools import search_web_general
from .domain_guard import is_out_of_domain
import re

BANNED_WORDS = [
    "fuck", "shit", "bitch", "asshole", "cunt", "dick", "pussy", "bastard", "slut", "whore",
    # Discriminatory / Racial
    "nigger", "nigga", "chink", "spic", "faggot", "fag", "dyke", "tranny", "retard"
]
BANNED_REGEX = re.compile(rf"\b({'|'.join(BANNED_WORDS)})\b", flags=re.IGNORECASE)

def check_toxicity(text: str) -> Tuple[bool, Dict[str, Any]]:
    # ponytail: naive regex instead of PyTorch model for toxicity
    return (True, {"toxicity": 1.0}) if (text and text.strip() and BANNED_REGEX.search(text)) else (False, {})

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """
You are a highly intelligent, comprehensive, and friendly assistant for Guru Nanak Dev Engineering College (GNDEC), Ludhiana.

Your primary goal is to provide EXTREMELY detailed, highly comprehensive, and exhaustive answers based on the retrieved knowledge.

CRITICAL RULES:
1. Greet the user naturally only if they greet you.
2. YOU MUST BE EXHAUSTIVE. Extract and present EVERY SINGLE RELEVANT DETAIL from the provided context. If the user asks for a fee structure, list the EXACT fees for EVERY SINGLE program, category (Boys/Girls, SC/ST, Hosteller, etc.), and breakdown mentioned in the context. DO NOT summarize or cut it short.
3. Do NOT use markdown formatting — no asterisks, no bold, no bullet points with *, no headers with #, no backticks.
4. Write in plain natural language. Use numbered lists (1. 2. 3.) or simple line breaks to organize information clearly.
5. STRICTLY NO GENERAL KNOWLEDGE OR CODING: If the user asks you to write code (like C++, Python) or solve homework/math, YOU MUST REFUSE. Even if C++ or Math is mentioned in the college syllabus context, you are a college support bot, not a coding assistant. Say exactly: "I can't answer this, I only have knowledge about GNDEC college."
6. You must cite your sources inline using brackets based on the Document number provided in the context (e.g., "GNDEC offers 7 B.Tech programs [1].").
7. End your response with a polite follow-up question related to the user's inquiry (e.g., "Which specific program are you interested in?").
8. If the retrieved knowledge does not contain the answer, explicitly state "I do not have information about that." DO NOT guess or hallucinate any facts not present in the context.
9. If a question is completely unrelated to GNDEC or college matters, politely redirect the user by saying "I can't answer this, I only have knowledge about GNDEC college."
10. NEVER generate any inappropriate, discriminatory, racial, or offensive language.
11. ALWAYS provide the maximum amount of detail possible. Act like an expert counselor giving a complete breakdown.
12. STRICT SINGLE-LANGUAGE RULE: You must detect the primary language of the user's question (English, Hindi, or Punjabi) and reply ENTIRELY in that exact same language. 
- DO NOT mix multiple languages within a single response.
- NEVER use Hinglish or blend Hindi and English words together.
- If the user writes in Roman Punjabi (e.g. "ki haal hai"), reply in pure Punjabi.
- If the user writes in English, reply ONLY in English.
- If the user writes in Hindi, reply ONLY in Hindi.

Tone: Warm, highly detailed, exhaustive, and helpful. Plain text only.
"""

# FAISS retriever (sync function) — fetch top 5
retriever = get_retriever(5)

WARNING_TEXT = (
    "I'm sorry, I cannot answer that. "
    "Please refrain from using inappropriate, discriminatory, or offensive language. "
    "Ask me something about GNDEC — admissions, departments, facilities, or college life."
)

OOD_TEXT = (
    "I can't answer this, I only have knowledge about GNDEC college."
)


# ---------------- MEMORY -----------------
def _get_memory(phone: str, session_id: str) -> ConversationBufferMemory:
    key = f"gndec:{phone}:{session_id}"
    history = RedisChatMessageHistory(url=REDIS_URL, session_id=key, ttl=SESSION_TTL)

    return ConversationBufferMemory(
        memory_key="history",
        chat_memory=history,
        return_messages=True,
    )


# ---------------- NORMALIZE DOCS -----------------
def _normalize_docs(docs_raw: List[Any]) -> Tuple[str, List[Dict[str, Any]]]:
    parts: List[str] = []
    sources: List[Dict[str, Any]] = []

    for idx, d in enumerate(docs_raw):
        meta = d if isinstance(d, dict) else getattr(d, "metadata", {})

        q   = meta.get("question", "")
        a   = meta.get("answer", "")
        src = meta.get("source_file", "")

        sources.append(meta)
        parts.append(f"--- Document {idx+1} ---\nSource: {src}\nQuestion: {q}\nInformation:\n{a}\n-------------------")

    docs_text = "\n\n".join(parts)
    return docs_text, sources


# ---------------- BUILD PROMPT -----------------
async def build_prompt(
    query: str, phone: str, session_id: str, history_limit: int = 10
):
    memory = _get_memory(phone, session_id)
    hist_vars = memory.load_memory_variables({})
    hist_msgs = hist_vars.get("history", [])

    limited_history = hist_msgs[-history_limit:]
    history_text = "\n".join(f"{m.type}: {m.content}" for m in limited_history)

    logging.info(
        f"Using last {len(limited_history)} messages out of {len(hist_msgs)} in memory"
    )

    standalone_query = query
    # Skipped LLM rewrite step for much lower latency

    # RAG — retrieve relevant GNDEC knowledge
    docs_raw = await asyncio.to_thread(retriever, standalone_query)
    docs_text, sources = _normalize_docs(docs_raw)
    
    # Proactive web search removed to improve latency.

    prompt = f"""{SYSTEM_PROMPT}

Conversation history (last {history_limit} messages):
{history_text}

Relevant knowledge about GNDEC (use ONLY the relevant parts to build your answer):
{docs_text}

User question:
{query}

Instructions:
- Use the provided knowledge (RAG or Web Search) to answer the user's question.
- STRICTLY DO NOT GUESS OR HALLUCINATE. If the provided knowledge does not contain the answer, you must say "I do not have information about that." and suggest visiting gndec.ac.in.
- Do NOT use irrelevant knowledge.
- Write in plain text only. No markdown, no asterisks, no bold, no bullet points with *, no # headers.
- Use numbered lists (1. 2. 3.) or plain line breaks if listing items.
- If the knowledge covers the topic well, give a thorough answer.
- STRICT SINGLE-LANGUAGE RULE: Answer entirely in ONE language (the exact language the user typed). NEVER mix multiple languages. NEVER blend Hindi and English words.

Answer:
"""
    return prompt, sources, memory


# ============================
# SYNC RESPONSE (NON-STREAM)
# ============================
async def answer_sync(query: str, phone: str, session_id: str):
    logging.info(f"[SYNC] User({phone}:{session_id}) → {query!r}")
    memory = _get_memory(phone, session_id)

    # 1️⃣ Toxicity check
    toxic, _ = await asyncio.to_thread(check_toxicity, query)
    if toxic:
        memory.chat_memory.add_ai_message(WARNING_TEXT)
        await save_message(phone, session_id, "assistant", WARNING_TEXT)
        return {"answer": WARNING_TEXT, "sources": []}

    if await asyncio.to_thread(is_out_of_domain, query):
        memory.chat_memory.add_ai_message(OOD_TEXT)
        await save_message(phone, session_id, "assistant", OOD_TEXT)
        return {"answer": OOD_TEXT, "sources": []}

    # Build prompt with RAG context
    prompt, sources, memory = await build_prompt(query, phone, session_id)

    # Save user message
    memory.chat_memory.add_user_message(query)
    await save_message(phone, session_id, "user", query)

    # ---------------- LLM CALL ----------------
    logging.info(f"🟢🟢🟢 GNDEC PROMPT 🟢🟢🟢\n\n{prompt}\n\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")

    msg = await llm.ainvoke(prompt)
    ans = msg.content.strip()

    # Toxicity check on output
    ai_toxic, _ = await asyncio.to_thread(check_toxicity, ans)
    final = WARNING_TEXT if ai_toxic else ans

    memory.chat_memory.add_ai_message(final)
    await save_message(phone, session_id, "assistant", final)

    return {"answer": final, "sources": sources}


# ============================
# STREAMING RESPONSE
# ============================
async def answer_stream(query: str, phone: str, session_id: str):
    logging.info(f"[STREAM] User({phone}:{session_id}) → {query!r}")
    memory = _get_memory(phone, session_id)

    # Input moderation
    toxic, _ = await asyncio.to_thread(check_toxicity, query)
    if toxic:
        yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
        return

    if await asyncio.to_thread(is_out_of_domain, query):
        yield json.dumps({"type": "blocked", "message": OOD_TEXT}) + "\n"
        return

    prompt, sources, memory = await build_prompt(query, phone, session_id)

    memory.chat_memory.add_user_message(query)
    await save_message(phone, session_id, "user", query)

    # Send sources first
    yield json.dumps({"type": "sources", "sources": sources}) + "\n"

    acc = ""
    
    async for chunk in llm.astream(prompt):
        delta = chunk.content
        if not delta:
            continue
            
        # Strip Markdown as requested
        delta = re.sub(r'[*_#`]', '', delta)
            
        acc += delta
        
        # 🚀 CPU OPTIMIZATION: Only run heavy PyTorch toxicity check every 50 characters
        if len(acc) % 50 < len(delta):
            ai_toxic, _ = await asyncio.to_thread(check_toxicity, acc)
            if ai_toxic:
                memory.chat_memory.add_ai_message(WARNING_TEXT)
                await save_message(phone, session_id, "assistant", WARNING_TEXT)
                yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
                return
                
        yield json.dumps({"type": "content", "delta": delta}) + "\n"

    # 🚀 CPU OPTIMIZATION: Final toxicity check to catch trailing characters
    ai_toxic, _ = await asyncio.to_thread(check_toxicity, acc)
    if ai_toxic:
        memory.chat_memory.add_ai_message(WARNING_TEXT)
        await save_message(phone, session_id, "assistant", WARNING_TEXT)
        yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
        return

    memory.chat_memory.add_ai_message(acc)
    await save_message(phone, session_id, "assistant", acc)

    logging.info("Stream completed successfully")


# ============================
# CLEAR REDIS SESSION
# ============================
async def clear_redis_session(phone: str, session_ids: Iterable[str]) -> bool:
    """Clears Redis chat history for given session IDs."""

    if not session_ids:
        print("[clear_redis_session] ⚠️ No session IDs provided")
        return False

    session_ids = list(session_ids)
    print(f"[clear_redis_session] Clearing Redis for {len(session_ids)} session(s)")

    def _clear():
        cleared = 0
        for session_id in session_ids:
            key = f"gndec:{phone}:{session_id}"
            print(f"[clear_redis_session] → Clearing key: {key}")
            history = RedisChatMessageHistory(url=REDIS_URL, session_id=key)
            history.clear()
            cleared += 1
        return cleared

    cleared_count = await asyncio.to_thread(_clear)
    print(f"[clear_redis_session] ✅ Cleared {cleared_count} Redis session(s)")
    return cleared_count > 0

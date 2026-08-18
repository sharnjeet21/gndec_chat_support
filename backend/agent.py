# backend/agent.py
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Iterable
import urllib.parse

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory

from .vectorstore import get_retriever
from .llm.llm import client, LLM_MODEL
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
3. Use Markdown formatting to make the response highly readable. Use bold text, bullet points, headers, and lists where appropriate.
4. Dynamically choose the best method to represent data: use detailed Markdown tables for multi-variable data (like fee structures, varying criteria, or semester breakdowns), bulleted lists for features, and numbered lists for steps.
5. STRICTLY NO GENERAL KNOWLEDGE OR CODING: If the user asks you to write code (like C++, Python) or solve homework/math, YOU MUST REFUSE. Even if C++ or Math is mentioned in the college syllabus context, you are a college support bot, not a coding assistant. Say exactly: "I can't answer this, I only have knowledge about GNDEC college."
6. You must cite your sources inline using brackets based on the Document number provided in the context (e.g., "GNDEC offers 7 B.Tech programs [1].").
7. End your response with a polite follow-up question related to the user's inquiry (e.g., "Which specific program are you interested in?").
8. If the retrieved knowledge does not contain the answer, explicitly state "I do not have information about that." DO NOT guess or hallucinate any facts not present in the context.
9. If a question is completely unrelated to GNDEC or college matters, politely redirect the user by saying "I can't answer this, I only have knowledge about GNDEC college."
10. NEVER generate any inappropriate, discriminatory, racial, or offensive language.
11. ALWAYS provide the maximum amount of detail possible. Act like an expert counselor giving a complete breakdown.
- DO NOT mix multiple languages within a single response.
- NEVER use Hinglish or blend Hindi and English words together.

Tone: Warm, highly detailed, exhaustive, and helpful. Use Markdown for clarity.
"""

# FAISS retriever (sync function) — fetch top 8 for broad coverage
retriever = get_retriever(8)

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
    query: str, phone: str, session_id: str, lang: str = "auto", history_limit: int = 10
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

    lang_rule = "Answer entirely in ONE language (the exact language the user typed). NEVER mix languages."
    if lang == "en-IN":
        lang_rule = "Answer entirely in English."
    elif lang == "hi-IN":
        lang_rule = "Answer entirely in Hindi."
    elif lang == "pa-IN":
        lang_rule = "Answer entirely in Punjabi."

    prompt = f"""{SYSTEM_PROMPT}

Conversation history (last {history_limit} messages):
{history_text}

Relevant knowledge about GNDEC (use ONLY the relevant parts to build your answer):
{docs_text}

User question:
{query}

Instructions:
- Answer the user's question using ONLY the provided knowledge. Be BRIEF and FOCUSED.
- CRITICAL: ONLY generate fee tables if the user EXPLICITLY asks for 'fees' or 'fee structure'. If they only ask for 'courses' or 'programs', DO NOT output any fee tables.
- CRITICAL: If the user only asks for 'courses' or 'programs', DO NOT output any study schemes, syllabus, or detailed subject information. ONLY list the courses/programs offered.
- WHEN explicitly asked for fee structures, YOU MUST generate a SEPARATE Markdown table for EACH individual course/program (e.g., one table for B.Tech, one for M.Tech, etc.). Each table MUST use the EXACT following 14-column format to match the official admission website:
| Sr No. | Program | Semester | Hostel (Boys) | Hostel (Girls) | PMS (Total) | PMS (Hostel Boys) | PMS (Hostel Girls) | TFW (Total) | TFW (Hostel Boys) | TFW (Hostel Girls) | Gen (Total) | Gen (Hostel Boys) | Gen (Hostel Girls) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
Fill the rows with data from the knowledge context. Leave cells blank if data is missing. Do not summarize fee data.
- Dynamically choose the best Markdown formatting for other data: bulleted lists for criteria/features, numbered lists for steps.
- Check conversation history for context on follow-up questions.
- STRICTLY DO NOT GUESS OR HALLUCINATE. If the answer is not in the provided knowledge, say "I do not have information about that." and suggest visiting gndec.ac.in.
- Do NOT use irrelevant knowledge.
- Use standard Markdown format for tables, bold text, bullet points, etc. to organize information clearly.
- Format numbers clearly with spaces (e.g. "Rs. 50,000" not "Rs50000").
- STRICT SINGLE-LANGUAGE RULE: {lang_rule}
- Give your answer directly. No chain of thought, no thinking process, no <think> tags, no preamble.

Answer:
"""
    return prompt, sources, memory


# ============================
# SYNC RESPONSE (NON-STREAM)
# ============================
async def answer_sync(query: str, phone: str, session_id: str, lang: str = "auto"):
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
    prompt, sources, memory = await build_prompt(query, phone, session_id, lang)

    # Save user message
    memory.chat_memory.add_user_message(query)
    await save_message(phone, session_id, "user", query)

    # ---------------- LLM CALL ----------------
    logging.info(f"🟢🟢🟢 GNDEC PROMPT 🟢🟢🟢\n\n{prompt}\n\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=2048,
        frequency_penalty=0.5,
        presence_penalty=0.5
    )
    ans = response.choices[0].message.content.strip()

    # Toxicity check on output
    ai_toxic, _ = await asyncio.to_thread(check_toxicity, ans)
    final = WARNING_TEXT if ai_toxic else ans

    memory.chat_memory.add_ai_message(final)
    await save_message(phone, session_id, "assistant", final)

    return {"answer": final, "sources": sources}


# ============================
# STREAMING RESPONSE
# ============================
async def answer_stream(query: str, phone: str, session_id: str, lang: str = "auto"):
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

    prompt, sources, memory = await build_prompt(query, phone, session_id, lang)

    memory.chat_memory.add_user_message(query)
    await save_message(phone, session_id, "user", query)

    # Send sources first
    yield json.dumps({"type": "sources", "sources": sources}) + "\n"

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=4096,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        stream=True
    )

    acc = ""
    async for chunk in response:
        if not chunk.choices:
            continue
        # Important: only read content, ignore reasoning_content!
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
            
        # Kept Markdown formatting as requested by user
        # delta = re.sub(r'[*_#`]', '', delta)
            
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

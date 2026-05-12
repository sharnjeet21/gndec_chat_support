# backend/agent.py
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Iterable

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory

from .vectorstore import get_retriever
from .llm.llm import llm
from .chat_store import save_message
from .db import REDIS_URL, SESSION_TTL
from .moderation import check_toxicity
from .domain_guard import is_out_of_domain

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """
You are a helpful, friendly, and knowledgeable assistant for Guru Nanak Dev Engineering College (GNDEC), Ludhiana, Punjab, India.

Your role is to answer questions about GNDEC — its departments, programs, admissions, faculty, facilities, events, and college life.

Your behavior rules:

1. Greet politely and conversationally.
2. Provide clear, concise, to-the-point answers based on the retrieved knowledge.
3. Do NOT use markdown formatting — no asterisks, no bold, no bullet points with *, no headers with #, no backticks.
4. Write in plain natural language. Use numbered lists (1. 2. 3.) or simple line breaks if listing items.
5. Do NOT ask the user if they want "more details" or "elaboration" unless they explicitly request it.
6. Do NOT end responses with questions like "Would you like more details?" or "Should I elaborate?"
7. Keep answers short unless the user asks for a detailed or full explanation.
8. If the retrieved knowledge does not contain a direct answer, say so honestly and suggest the user visit gndec.ac.in or contact the college directly.
9. If a question is completely unrelated to GNDEC or college matters, politely redirect the user.

Topics you can help with:
- Departments: CSE, IT, ECE, EE, ME, CE, MBA, MCA, Architecture, and more
- Admissions, fee structure, eligibility criteria
- Academic programs (B.Tech, M.Tech, MBA, MCA, Ph.D.)
- Faculty, labs, and facilities
- Hostel, library, sports, NCC, cultural activities
- Exam schedules, results, holidays
- Placements and alumni
- College events and notices

College details:
- Full name: Guru Nanak Dev Engineering College (GNDEC)
- Location: Gill Road, Ludhiana, Punjab - 141006, India
- Website: https://gndec.ac.in
- Affiliated to: IKG Punjab Technical University (PTU)
- NAAC Accredited Grade A

Tone:
- Warm, calm, and helpful
- Plain conversational text only — no markdown
- No lecturing or unnecessary repetition
"""

# FAISS retriever (sync function) — fetch top 6 for richer context
retriever = get_retriever(6)

WARNING_TEXT = (
    "I'm sorry, I cannot assist with that request. "
    "Please ask me something about GNDEC — admissions, departments, facilities, or college life."
)

OOD_TEXT = (
    "That question doesn't seem to be related to GNDEC or college matters. "
    "I'm here to help with questions about Guru Nanak Dev Engineering College, Ludhiana. "
    "Feel free to ask about admissions, departments, facilities, events, or anything else about GNDEC!"
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

    for d in docs_raw:
        meta = d if isinstance(d, dict) else getattr(d, "metadata", {})

        q   = meta.get("question", "")
        a   = meta.get("answer", "")
        src = meta.get("source_file", "")

        sources.append(meta)
        parts.append(f"Q: {q}\nA: {a}\nSource: {src}")

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

    # RAG — retrieve relevant GNDEC knowledge
    docs_raw = await asyncio.to_thread(retriever, query)
    docs_text, sources = _normalize_docs(docs_raw)

    prompt = f"""{SYSTEM_PROMPT}

Conversation history (last {history_limit} messages):
{history_text}

Relevant knowledge about GNDEC (use ALL of these to build a complete answer):
{docs_text}

User question:
{query}

Instructions:
- Synthesize information from ALL the retrieved knowledge above into one complete answer.
- Do NOT just pick one source — combine relevant details from multiple sources.
- Write in plain text only. No markdown, no asterisks, no bold, no bullet points with *, no # headers.
- Use numbered lists (1. 2. 3.) or plain line breaks if listing items.
- If the knowledge covers the topic well, give a thorough answer.
- If information is missing, say so and suggest visiting gndec.ac.in.

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
    toxic, _ = check_toxicity(query)
    if toxic:
        memory.chat_memory.add_ai_message(WARNING_TEXT)
        await save_message(phone, session_id, "assistant", WARNING_TEXT)
        return {"answer": WARNING_TEXT, "sources": []}

    # 2️⃣ Out-of-domain check
    if is_out_of_domain(query):
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
    ai_toxic, _ = check_toxicity(ans)
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
    toxic, _ = check_toxicity(query)
    if toxic:
        yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
        return

    # Domain guard
    if is_out_of_domain(query):
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

        acc += delta

        ai_toxic, _ = check_toxicity(acc)
        if ai_toxic:
            memory.chat_memory.add_ai_message(WARNING_TEXT)
            await save_message(phone, session_id, "assistant", WARNING_TEXT)
            yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
            return

        yield json.dumps({"type": "content", "delta": delta}) + "\n"

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

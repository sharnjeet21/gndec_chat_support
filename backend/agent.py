# backend/agent.py
import json
import asyncio
import logging
import os
import re
from typing import List, Dict, Any, Tuple, Iterable

from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory, ChatMessageHistory
from openai import AsyncOpenAI

from .vectorstore import get_retriever
from .llm.llm import client, LLM_MODEL
from .chat_store import save_message
from .db import REDIS_URL, SESSION_TTL
from .domain_guard import is_out_of_domain

BANNED_WORDS = [
    "fuck", "shit", "bitch", "asshole", "cunt", "dick", "pussy", "bastard", "slut", "whore",
    "nigger", "nigga", "chink", "spic", "faggot", "fag", "dyke", "tranny", "retard"
]
BANNED_REGEX = re.compile(rf"\b({'|'.join(BANNED_WORDS)})\b", flags=re.IGNORECASE)

openai_key = os.getenv("OPENAI_API_KEY", "")
is_openai_official = openai_key.startswith("sk-") and "openai.com" in os.getenv("MODEL_API_URL", "https://api.openai.com")
mod_client = AsyncOpenAI(api_key=openai_key) if is_openai_official else None

async def check_toxicity(text: str) -> Tuple[bool, Dict[str, Any]]:
    if not text or not text.strip():
        return False, {}
    if mod_client:
        try:
            res = await mod_client.moderations.create(input=text)
            flagged = res.results[0].flagged
            return flagged, {"toxicity": 1.0 if flagged else 0.0}
        except Exception as e:
            logging.error(f"Moderation API error: {e}")
    return (True, {"toxicity": 1.0}) if BANNED_REGEX.search(text) else (False, {})

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """
You are a knowledgeable and helpful assistant for Guru Nanak Dev Engineering College (GNDEC), Ludhiana.

CRITICAL RULES:
1. Greet the user naturally only if they greet you.
2. Answer the user's question directly using ONLY the provided knowledge context.
3. Use clean Markdown formatting: bold text, bullet points, headers, and lists where appropriate.
4. If asked for a list of courses/programs (e.g. B.Tech branches), provide a clean bulleted list of the program/branch names.
5. STRICTLY NO GENERAL KNOWLEDGE OR CODING: If asked to write code (C++, Python) or solve general homework, refuse by saying: "I can't answer this, I only have knowledge about GNDEC college."
6. Cite sources inline using brackets based on the document numbers provided in context (e.g., [1]).
7. If the retrieved knowledge does not contain the answer, state: "I do not have information about that." and suggest checking gndec.ac.in.
8. NEVER generate offensive or discriminatory language.
9. DO NOT mix multiple languages in a single response.

Tone: Warm, direct, precise, and helpful.
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
_local_memories: Dict[str, ChatMessageHistory] = {}

def _get_memory(phone: str, session_id: str) -> ConversationBufferWindowMemory:
    key = f"gndec:{phone}:{session_id}"
    try:
        history = RedisChatMessageHistory(url=REDIS_URL, session_id=key, ttl=SESSION_TTL)
        _ = history.messages
    except Exception as e:
        logging.warning(f"Redis memory unavailable ({e}), using in-memory fallback.")
        if key not in _local_memories:
            _local_memories[key] = ChatMessageHistory()
        history = _local_memories[key]

    return ConversationBufferWindowMemory(
        memory_key="history",
        chat_memory=history,
        return_messages=True,
        k=10
    )


# ---------------- QUERY REWRITING & TRANSLATION -----------------
REGIONAL_MAP = {
    "kinni": "fee structure amount",
    "kinna": "fee structure amount",
    "kitni": "fee structure amount",
    "kitna": "fee structure amount",
    "kado": "date schedule timing",
    "kab": "date schedule timing",
    "kithe": "location address",
    "kaha": "location address",
    "dakhla": "admission apply",
    "dakhle": "admissions",
    "kholna": "open reopening date",
    "khulna": "open reopening date",
    "chahida": "required eligibility",
    "chahiye": "required eligibility",
    "clg": "GNDEC college",
    "hostel da": "hostel",
    "hostel di": "hostel",
    "ਫੀਸ": "fee structure",
    "ਦਾਖਲਾ": "admission",
    "ਹੋਸਟਲ": "hostel",
    "ਕਦੋਂ": "when schedule date",
    "ਕਿੱਥੇ": "where location",
    "फीस": "fee structure",
    "दाखिला": "admission",
    "हॉस्टल": "hostel",
    "कब": "when schedule date",
    "कहाँ": "where location"
}

def rewrite_query(query: str, history_msgs: list = None) -> str:
    """
    Expands multilingual/slang query and resolves conversational coreference pronouns
    using recent conversation history for 100% precision retrieval.
    """
    if not query:
        return ""
    q = query.strip()
    q_lower = q.lower()

    # 1. Regional / Slang Expansion
    expanded_text = q_lower
    for k, v in REGIONAL_MAP.items():
        if k in expanded_text:
            expanded_text = expanded_text.replace(k, v)

    # 2. Guard broad/standalone queries from inheriting historical entities
    broad_triggers = {
        "fee", "fees", "fee structure", "college fee", "college fees", "hostel fee", "hostel fees",
        "courses", "programs", "all courses", "all programs", "branches", "departments",
        "admissions", "admission", "placements", "placement", "facilities", "about gndec"
    }
    if q_lower in broad_triggers or q_lower.startswith("all ") or q_lower.startswith("list all"):
        return expanded_text

    # 3. Multi-turn Pronoun & Topic Coreference Resolution (strictly for follow-ups with pronouns or referential cues)
    if history_msgs:
        pronouns = {"he", "she", "his", "her", "him", "they", "their", "them", "it", "its", "that", "this", "these", "those", "same"}
        attr_cues = {"qualification", "email", "phone", "contact", "office", "cabin", "hod", "head", "credits", "syllabus"}
        query_words = set(re.findall(r"[a-zA-Z0-9]+", q_lower))

        has_pronoun = bool(query_words.intersection(pronouns))
        has_attr_cue = bool(query_words.intersection(attr_cues))

        if has_pronoun or (has_attr_cue and len(query_words) <= 5):
            history_text = " ".join([
                (m.content if hasattr(m, "content") else str(m))
                for m in history_msgs[-4:]
            ])

            # Extract names with titles
            names = re.findall(r"(?:Dr\.|Prof\.|Er\.|Mr\.|Mrs\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", history_text)
            # Extract departments / branches
            depts = re.findall(
                r"\b(Computer Science|Information Technology|Mechanical Engineering|Civil Engineering|Electrical Engineering|Electronics|Production|Applied Science|CSE|ECE|IT|EE|B\.?Tech|M\.?Tech|BCA|MCA|MBA)\b",
                history_text,
                re.IGNORECASE
            )

            cues = []
            if names:
                cues.append(names[-1])
            elif depts:
                cues.append(depts[-1])

            if cues:
                expanded_text = f"{expanded_text} {' '.join(cues)}"

    return expanded_text


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


# ---------------- DIRECT STRUCTURED RESPONSES -----------------
def is_direct_fee_query(query: str, sources: List[Dict[str, Any]]) -> bool:
    """Checks if query is a fee structure lookup matching official fee tables."""
    if not sources:
        return False
    if not all(s.get("source_file") == "admission.gndec.ac.in/Fee_Structure.php" for s in sources):
        return False
    q_lower = query.lower()
    fee_triggers = {"fee", "fees", "cost", "kharcha", "paisa", "structure", "hostel", "charges", "amount", "tution", "tuition", "pms", "tfw"}
    return any(k in q_lower for k in fee_triggers)


def build_direct_fee_response(sources: List[Dict[str, Any]], lang: str = "auto") -> str:
    """Formats exact 14-column official fee tables into response."""
    if lang == "hi-IN":
        intro = "गुरु नानक देव इंजीनियरिंग कॉलेज (GNDEC), लुधियाना का आधिकारिक शुल्क विवरण [1]:\n\n"
        outro = "\n\nआप किस विशिष्ट कार्यक्रम या सेमेस्टर के बारे में अधिक जानकारी चाहते हैं?"
    elif lang == "pa-IN":
        intro = "ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਇੰਜੀਨੀਅਰਿੰਗ ਕਾਲਜ (GNDEC), ਲੁਧਿਆਣਾ ਦਾ ਅਧਿਕਾਰਤ ਫੀਸ ਵੇਰਵਾ [1]:\n\n"
        outro = "\n\nਤੁਸੀਂ ਕਿਸ ਖਾਸ ਕੋਰਸ ਜਾਂ ਸਮੈਸਟਰ ਬਾਰੇ ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੁੰਦੇ ਹੋ?"
    else:
        intro = "Here is the official fee structure for Guru Nanak Dev Engineering College (GNDEC), Ludhiana [1]:\n\n"
        outro = "\n\nWhich specific program or semester would you like to know more about?"

    tables = []
    for s in sources:
        ans = s.get("answer", "").strip()
        if ans:
            tables.append(ans)

    return intro + "\n\n".join(tables) + outro


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

    standalone_query = rewrite_query(query, limited_history)
    logging.info(f"[QUERY REWRITE] Original: {query!r} -> Search query: {standalone_query!r}")

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

Relevant knowledge about GNDEC:
{docs_text}

User question:
{query}

Instructions:
- Answer the user's question directly using ONLY the provided GNDEC knowledge.
- If the user asks for courses or branches, give a clear bulleted list of the course/branch names.
- If asked a follow-up question, use the conversation history to understand pronouns and context.
- STRICTLY DO NOT GUESS OR HALLUCINATE. If the answer is not in the knowledge context, state "I do not have information about that." and suggest visiting gndec.ac.in.
- Use clean Markdown format (bullet points, bold text).
- STRICT SINGLE-LANGUAGE RULE: {lang_rule}
- Give your answer directly without preamble, thinking process, or meta-comments.

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
    toxic, _ = await check_toxicity(query)
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
    # Intercept direct structured fee queries to avoid LLM token repetition timeouts
    if is_direct_fee_query(query, sources):
        logging.info("Interception: Routing direct structured fee response (0ms latency, zero hallucinations).")
        final = build_direct_fee_response(sources, lang)
        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        return {"answer": final, "sources": sources}

    logging.info(f"🟢🟢🟢 GNDEC PROMPT 🟢🟢🟢\n\n{prompt}\n\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=4096,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    ans = response.choices[0].message.content.strip()

    # Toxicity check on output
    ai_toxic, _ = await check_toxicity(ans)
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
    toxic, _ = await check_toxicity(query)
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

    # Intercept direct structured fee queries to avoid LLM token repetition timeouts
    if is_direct_fee_query(query, sources):
        logging.info("Interception: Streaming direct structured fee response (smooth delivery, zero hallucinations).")
        final = build_direct_fee_response(sources, lang)
        for line in final.split("\n"):
            yield json.dumps({"type": "content", "delta": line + "\n"}) + "\n"
            await asyncio.sleep(0.005)

        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        logging.info("Stream completed successfully (Direct structured fee response)")
        return

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=4096,
        frequency_penalty=0.0,
        presence_penalty=0.0,
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
            
        acc += delta
        
        # 🚀 CPU OPTIMIZATION: Only run toxicity check every 500 characters
        if len(acc) % 500 < len(delta):
            ai_toxic, _ = await check_toxicity(acc)
            if ai_toxic:
                memory.chat_memory.add_ai_message(WARNING_TEXT)
                await save_message(phone, session_id, "assistant", WARNING_TEXT)
                yield json.dumps({"type": "blocked", "message": WARNING_TEXT}) + "\n"
                return
                
        yield json.dumps({"type": "content", "delta": delta}) + "\n"

    # 🚀 CPU OPTIMIZATION: Final toxicity check to catch trailing characters
    ai_toxic, _ = await check_toxicity(acc)
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
        logging.warning("[clear_redis_session] ⚠️ No session IDs provided")
        return False

    session_ids = list(session_ids)
    logging.info(f"[clear_redis_session] Clearing Redis for {len(session_ids)} session(s)")

    def _clear():
        cleared = 0
        for session_id in session_ids:
            key = f"gndec:{phone}:{session_id}"
            logging.info(f"[clear_redis_session] → Clearing key: {key}")
            history = RedisChatMessageHistory(url=REDIS_URL, session_id=key)
            history.clear()
            cleared += 1
        return cleared

    cleared_count = await asyncio.to_thread(_clear)
    logging.info(f"[clear_redis_session] ✅ Cleared {cleared_count} Redis session(s)")
    return cleared_count > 0

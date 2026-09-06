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

from .vectorstore import get_retriever, encode_query, find_faculty_matches, find_fee_structure_matches
from .llm.llm import client, LLM_MODEL, call_model_async, call_model_stream
from .chat_store import save_message
from .db import REDIS_URL, SESSION_TTL
from .domain_guard import is_out_of_domain
from .cache import global_semantic_cache
from .verify import check_sensitive_or_unanswerable, verify_groundedness, strip_scrape_leaks

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
You are an expert official assistant for Guru Nanak Dev Engineering College (GNDEC), Ludhiana.

CRITICAL RULES:
1. Answer the user's specific question directly using facts from the relevant document in the knowledge context.
2. DO NOT output conversational filler, introductory pleasantries, or generic welcomes (e.g. "Welcome to GNDEC!"). Start directly with the answer.
3. Be comprehensive: include all specific details, facilities, statistics, numbers, library volumes, hostel amenities, course outlines, and contact numbers present in the context.
4. If asked for a list of courses/programs (e.g. B.Tech branches), provide a clean bulleted list of the program/branch names.
5. STRICTLY NO GENERAL KNOWLEDGE OR CODING: If asked to write code (C++, Python) or solve general homework, refuse by saying: "I can't answer this, I only have knowledge about GNDEC college."
6. Cite sources inline using brackets based on the document numbers provided in context (e.g., [1]).
7. If the retrieved knowledge does not contain the answer, state: "I do not have information about that." and suggest checking gndec.ac.in.
8. NEVER generate offensive or discriminatory language.
9. DO NOT mix multiple languages in a single response.

Tone: Direct, factual, precise, and professional.
"""

# FAISS retriever (sync function) — fetch top 4 high-precision reranked chunks for fast CPU inference
retriever = get_retriever(4)

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
    "kahan": "location address",
    "dakhla": "admission apply eligibility",
    "dakhle": "admissions apply eligibility",
    "kholna": "open reopening date",
    "khulna": "open reopening date",
    "chahida": "required eligibility criteria",
    "chahiye": "required eligibility criteria",
    "clg": "GNDEC college",
    "hostel da": "hostel",
    "hostel di": "hostel",
    "hostel de": "hostel",
    "ਮਿਲਦਾ": "available facility",
    "ਮਿਲਦੀ": "available facility",
    "ਫੀਸ": "fee structure",
    "ਫੀਸਾਂ": "fee structure",
    "ਦਾਖਲਾ": "admission eligibility",
    "ਦਾਖ਼ਲਾ": "admission eligibility",
    "ਦਾਖਲੇ": "admissions eligibility",
    "ਦਾਖ਼ਲੇ": "admissions eligibility",
    "ਯੋਗਤਾ": "eligibility criteria 10+2",
    "ਕਾਲਜ": "GNDEC college",
    "ਹੋਸਟਲ": "hostel facilities accommodation",
    "ਕਦੋਂ": "when schedule date",
    "ਕਿੱਥੇ": "where location",
    "ਕੋਰਸ": "courses programs degrees",
    "ਕੋਰਸਾਂ": "courses programs degrees",
    "ਬ੍ਰਾਂਚ": "branch branches",
    "ਬ੍ਰਾਂਚਾਂ": "branches",
    "ਕਿਹੜੇ-ਕਿਹੜੇ": "which list all programs courses degrees",
    "ਕਿਹੜੇ ਕਿਹੜੇ": "which list all programs courses degrees",
    "ਕਿਹੜੀਆਂ-ਕਿਹੜੀਆਂ": "which list all programs courses degrees",
    "ਕਿਹੜੀਆਂ ਕਿਹੜੀਆਂ": "which list all programs courses degrees",
    "ਕਿਹੜੇ": "which list programs",
    "ਕਿਹੜੀਆਂ": "which list programs",
    "ਕਿਹੜਾ": "which",
    "ਕਿਹੜੀ": "which",
    "ਸਾਰੇ": "all",
    "ਪ੍ਰੋਗਰਾਮ": "programs courses degrees",
    "ਪੜ੍ਹਾਏ ਜਾਂਦੇ ਹਨ": "taught offered courses programs",
    "ਪੜ੍ਹਾਈ": "courses curriculum",
    "ਵਿਭਾਗ": "departments",
    "ਪ੍ਰੋਫੈਸਰ": "professors faculty",
    "ਅਧਿਆਪਕ": "faculty teachers",
    "ਲਿਸਟ": "list all",
    "ਡਾਕਟਰ": "doctorate PhD",
    "ਪੀਐਚਡੀ": "PhD doctorate",
    "ਡਾਕਟਰੇਟ": "PhD doctorate",
    "ਪਲੇਸਮੈਂਟ": "placement jobs salary package",
    "ਖੇਡਾਂ": "sports physical education",
    "ਲਾਈਬ੍ਰੇਰੀ": "library",
    "ਵਜ਼ੀਫ਼ਾ": "scholarship PMS TFW",
    "ਵਜ਼ੀਫ਼ੇ": "scholarship PMS TFW",
    "ਸਕਾਲਰਸ਼ਿਪ": "scholarship PMS TFW",
    "फीस": "fee structure",
    "दाखिला": "admission eligibility",
    "दाखिले": "admissions eligibility",
    "योग्यता": "eligibility criteria 10+2",
    "कॉलेज": "GNDEC college",
    "हॉस्टल": "hostel accommodation",
    "कब": "when schedule date",
    "कहाँ": "where location",
    "कहा": "where location",
    "कोर्स": "courses programs degrees",
    "शाखाएं": "branches",
    "विभाग": "departments",
    "प्रोफेसर": "professors faculty",
    "शिक्षक": "faculty teachers",
    "छात्रवृत्ति": "scholarship PMS TFW",
    "छात्रवृत्तियां": "scholarship PMS TFW",
    "कौन-कौन से": "which list all courses programs",
    "कौन कौन से": "which list all courses programs",
    "पढ़ाए जाते हैं": "taught offered courses programs"
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
def _normalize_docs(docs_raw: List[Any], max_doc_chars: int = 1200) -> Tuple[str, List[Dict[str, Any]]]:
    parts: List[str] = []
    sources: List[Dict[str, Any]] = []

    for idx, d in enumerate(docs_raw):
        meta = d if isinstance(d, dict) else getattr(d, "metadata", {})

        q   = meta.get("question", "")
        a   = meta.get("answer", "")
        src = meta.get("source_file", "")
        is_aggregate = meta.get("is_aggregate", False)

        # Preserve structured faculty/course/fee/admission documents entirely — these are verified facts,
        # not scraped web text. Truncation causes hallucinations (fake branches, incomplete PhD lists).
        if is_aggregate and src in ("faculty.json", "courses_offered.json", "fee_structures.json", "admission.gndec.ac.in"):
            pass  # keep full verified data
        elif a and len(a) > max_doc_chars and not a.strip().startswith("|"):
            a = a[:max_doc_chars] + "... [truncated for brevity]"

        sources.append(meta)
        parts.append(f"--- Document {idx+1} ---\nSource: {src}\nQuestion: {q}\nInformation:\n{a}\n-------------------")

    docs_text = "\n\n".join(parts)
    return docs_text, sources


# ---------------- DIRECT STRUCTURED RESPONSES -----------------
def is_direct_fee_query(query: str, sources: List[Dict[str, Any]]) -> bool:
    """Checks if query is a fee structure lookup matching official fee tables."""
    if not sources:
        return False
    # Accept known fee table sources (FAISS index paths + structured matcher)
    fee_sources = {"admission.gndec.ac.in/Fee_Structure.php", "gndec.ac.in/?q=node/572", "_structured_fee"}
    has_fee = any(s.get("source_file") in fee_sources for s in sources)
    if not has_fee:
        return False
    q_lower = query.lower()
    fee_triggers = {"fee", "fees", "cost", "kharcha", "paisa", "structure", "hostel", "charges", "amount", "tution", "tuition", "pms", "tfw", "scholarship", "waiver"}
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
        src = s.get("source_file", "")
        ans = s.get("answer", "").strip()
        if not ans:
            continue
        if src in ("admission.gndec.ac.in/Fee_Structure.php", "gndec.ac.in/?q=node/572", "_structured_fee"):
            tables.append(ans)

    return intro + "\n\n".join(tables) + outro


def is_direct_faculty_query(query: str, sources: List[Dict[str, Any]]) -> bool:
    """Checks if query is an aggregate faculty directory lookup (PhD, HODs, Department roster)."""
    if not sources:
        return False
    # Check for faculty source in FAISS sources OR check if structured faculty matcher returned data
    has_faiss_faculty = any(s.get("source_file") == "faculty.json" and s.get("is_aggregate") for s in sources)
    has_structured_faculty = any(s.get("source_file") == "_structured_faculty" for s in sources)
    if not (has_faiss_faculty or has_structured_faculty):
        return False
    q_lower = query.lower()
    triggers = {
        "faculty", "faculties", "teacher", "teachers", "professor", "professors",
        "hod", "hods", "head", "phd", "ph.d", "doctorate", "doctorates", "doctoral",
        "staff", "roster", "directory"
    }
    return any(k in q_lower for k in triggers)


def build_direct_faculty_response(sources: List[Dict[str, Any]], lang: str = "auto") -> str:
    """Formats structured faculty directory tables into response."""
    if lang == "hi-IN":
        intro = "गुरु नानक देव इंजीनियरिंग कॉलेज (GNDEC), लुधियाना का आधिकारिक संकाय विवरण [1]:\n\n"
        outro = "\n\nक्या आप किसी विशिष्ट संकाय सदस्य या विभाग के बारे में अधिक जानकारी चाहते हैं?"
    elif lang == "pa-IN":
        intro = "ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਇੰਜੀਨੀਅਰਿੰਗ ਕਾਲਜ (GNDEC), ਲੁਧਿਆਣਾ ਦਾ ਅਧਿਕਾਰਤ ਫੈਕਲਟੀ ਵੇਰਵਾ [1]:\n\n"
        outro = "\n\nਕੀ ਤੁਸੀਂ ਕਿਸੇ ਖਾਸ ਫੈਕਲਟੀ ਮੈਂਬਰ ਜਾਂ ਵਿਭਾਗ ਬਾਰੇ ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੁੰਦੇ ਹੋ?"
    else:
        intro = "Here is the official faculty directory for Guru Nanak Dev Engineering College (GNDEC), Ludhiana [1]:\n\n"
        outro = "\n\nWould you like more details about any specific faculty member or department?"

    tables = []
    for s in sources:
        src = s.get("source_file", "")
        ans = s.get("answer", "").strip()
        if not ans:
            continue
        if src == "faculty.json" or src == "_structured_faculty":
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

    # Language detection if auto
    detected_lang = lang
    if lang == "auto":
        if re.search(r"[਀-੿]", query):
            detected_lang = "pa-IN"
        elif re.search(r"[ऀ-ॿ]", query):
            detected_lang = "hi-IN"

    lang_rule = "Answer entirely in ONE language (the exact language the user typed). NEVER mix languages."
    if detected_lang == "en-IN":
        lang_rule = "Answer entirely in English."
    elif detected_lang == "hi-IN":
        lang_rule = "Answer entirely in Hindi (Devanagari script)."
    elif detected_lang == "pa-IN":
        lang_rule = "Answer entirely in Punjabi (Gurmukhi script)."

    prompt = f"""{SYSTEM_PROMPT}

Conversation history (last {history_limit} messages):
{history_text}

Relevant knowledge about GNDEC:
{docs_text}

User question:
{query}

Instructions:
- Answer the user's question directly using facts from the matching GNDEC document.
- Start immediately with the factual answer; do NOT start with conversational greetings, pleasantries, or preamble.
- Be comprehensive and retain key specific entities, facilities, numbers, volumes, mess/hostel amenities, roles, titles, doctor/medical staff, qualifications, and contact details present in the context.
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

    # 1.5️⃣ Sensitive / unanswerable query abstention (private data, credentials, dynamic menus)
    sensitive_refusal = check_sensitive_or_unanswerable(query)
    if sensitive_refusal:
        memory.chat_memory.add_ai_message(sensitive_refusal)
        await save_message(phone, session_id, "assistant", sensitive_refusal)
        return {"answer": sensitive_refusal, "sources": []}

    # 2️⃣ Semantic Cache Lookup (Pre-Retrieval)
    q_vec = None
    try:
        q_vec = await asyncio.to_thread(encode_query, query)
        cached_result = global_semantic_cache.lookup(query, query_vec=q_vec)
        if cached_result:
            logging.info(f"⚡ SemanticCache HIT: Serving instant response for {query!r}")
            c_ans = cached_result.get("answer", "")
            c_src = cached_result.get("sources", [])
            memory.chat_memory.add_user_message(query)
            memory.chat_memory.add_ai_message(c_ans)
            await save_message(phone, session_id, "user", query)
            await save_message(phone, session_id, "assistant", c_ans)
            return {"answer": c_ans, "sources": c_src, "cached": True}
    except Exception as e:
        logging.warning(f"SemanticCache lookup skipped: {e}")

    # Build prompt with RAG context
    prompt, sources, memory = await build_prompt(query, phone, session_id, lang)

    # Save user message
    memory.chat_memory.add_user_message(query)
    await save_message(phone, session_id, "user", query)

    # 2.5️⃣ Inject structured matchers into sources for routing decisions.
    # These are loaded at startup in vectorstore.py module scope.
    try:
        fac_matches = find_faculty_matches(query)
        if fac_matches:
            for fm in fac_matches:
                meta = fm.metadata if hasattr(fm, "metadata") else (fm if isinstance(fm, dict) else {})
                sources.append({"source_file": "_structured_faculty", "answer": meta.get("answer", ""), "question": meta.get("question", "")})
    except Exception as e:
        logging.warning(f"find_faculty_matches skipped: {e}")

    # Inject structured fee matches too
    try:
        fee_matches = find_fee_structure_matches(query)
        if fee_matches:
            for fm in fee_matches:
                meta = fm.metadata if hasattr(fm, "metadata") else (fm if isinstance(fm, dict) else {})
                sources.append({"source_file": "_structured_fee", "answer": meta.get("answer", ""), "question": meta.get("question", "")})
    except Exception as e:
        logging.warning(f"find_fee_structure_matches skipped: {e}")

    # ---------------- LLM CALL ----------------
    # Intercept direct structured fee queries to avoid LLM token repetition timeouts
    if is_direct_fee_query(query, sources):
        logging.info("Interception: Routing direct structured fee response (0ms latency, zero hallucinations).")
        final = build_direct_fee_response(sources, lang)
        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        try:
            global_semantic_cache.store(query, q_vec, {"answer": final, "sources": sources})
        except Exception:
            pass
        return {"answer": final, "sources": sources}

    # Intercept direct aggregate faculty queries to deliver complete structured directories
    if is_direct_faculty_query(query, sources):
        logging.info("Interception: Routing direct structured faculty response (0ms latency, zero hallucinations).")
        final = build_direct_faculty_response(sources, lang)
        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        try:
            global_semantic_cache.store(query, q_vec, {"answer": final, "sources": sources})
        except Exception:
            pass
        return {"answer": final, "sources": sources}

    logging.info(f"🟢🟢🟢 GNDEC PROMPT 🟢🟢🟢\n\n{prompt}\n\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")

    ans = await call_model_async(prompt, max_tokens=768)

    # Strip any reasoning-scratchpad leaks before further processing
    ans = strip_scrape_leaks(ans)

    # Toxicity check on output
    ai_toxic, _ = await check_toxicity(ans)
    final = WARNING_TEXT if ai_toxic else ans

    # Store in semantic cache if not toxic/warning
    if not ai_toxic and final != WARNING_TEXT:
        try:
            global_semantic_cache.store(query, q_vec, {"answer": final, "sources": sources})
        except Exception:
            pass

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

    # Sensitive / unanswerable query abstention
    sensitive_refusal = check_sensitive_or_unanswerable(query)
    if sensitive_refusal:
        yield json.dumps({"type": "blocked", "message": sensitive_refusal}) + "\n"
        return

    # Semantic Cache Lookup (Pre-Retrieval)
    q_vec = None
    try:
        q_vec = await asyncio.to_thread(encode_query, query)
        cached_result = global_semantic_cache.lookup(query, query_vec=q_vec)
        if cached_result:
            logging.info(f"⚡ SemanticCache HIT (Stream): Serving instant cached response for {query!r}")
            c_ans = cached_result.get("answer", "")
            c_src = cached_result.get("sources", [])
            yield json.dumps({"type": "sources", "sources": c_src}) + "\n"
            for line in c_ans.split("\n"):
                yield json.dumps({"type": "content", "delta": line + "\n"}) + "\n"
                await asyncio.sleep(0.002)
            memory.chat_memory.add_user_message(query)
            memory.chat_memory.add_ai_message(c_ans)
            await save_message(phone, session_id, "user", query)
            await save_message(phone, session_id, "assistant", c_ans)
            return
    except Exception as e:
        logging.warning(f"SemanticCache stream lookup skipped: {e}")

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

    # Intercept direct aggregate faculty queries to deliver complete structured directories
    if is_direct_faculty_query(query, sources):
        logging.info("Interception: Streaming direct structured faculty response (smooth delivery, zero hallucinations).")
        final = build_direct_faculty_response(sources, lang)
        for line in final.split("\n"):
            yield json.dumps({"type": "content", "delta": line + "\n"}) + "\n"
            await asyncio.sleep(0.005)

        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        logging.info("Stream completed successfully (Direct structured faculty response)")
        return

    acc = ""
    async for delta in call_model_stream(prompt, max_tokens=768):
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

    # Strip any reasoning-scratchpad leaks before storing/caching
    acc = strip_scrape_leaks(acc)

    # Store in semantic cache if not toxic/warning
    if not ai_toxic and acc != WARNING_TEXT:
        try:
            global_semantic_cache.store(query, q_vec, {"answer": acc, "sources": sources})
        except Exception:
            pass

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

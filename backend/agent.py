# backend/agent.py
import json
import asyncio
import logging
import os
import re
from typing import List, Dict, Any, Tuple, Iterable, AsyncGenerator

try:
    from langchain.memory import ConversationBufferWindowMemory
except (ImportError, ModuleNotFoundError):
    from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory, ChatMessageHistory
from openai import AsyncOpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .vectorstore import get_retriever, encode_query, find_faculty_matches, find_fee_structure_matches
from .llm.llm import call_model_async, call_model_async_stream as call_model_stream
from .chat_store import save_message
from .db import REDIS_URL, SESSION_TTL
from .domain_guard import is_out_of_domain
from .cache import global_semantic_cache
from .verify import check_sensitive_or_unanswerable, verify_groundedness, strip_scrape_leaks, ABSTENTION_MESSAGE

# Import the new RAG pipeline
from .rag import answer_query, create_default_pipeline
from .rag.contracts import PipelineContext, VerificationStatus


# --- Constants & globals ---

API_KEY = os.getenv("API_KEY", "naman@1234")

WARNING_TEXT = (
    "I'm here to help with factual questions about GNDEC college. "
    "Please keep your queries respectful and on-topic. "
    "If you have concerns about this response, contact the admin."
)

OOD_TEXT = (
    "I am the official information assistant strictly for Guru Nanak Dev Engineering College (GNDEC), Ludhiana. "
    "I can only answer questions about GNDEC college. "
    "For inquiries regarding other institutions (such as GNDU, GNDPC, or other colleges), please refer to their respective official websites."
)

# --- Memory (keep existing for backward compatibility with other components) ---

_memory_store: Dict[str, ConversationBufferWindowMemory] = {}


def format_source_item(doc: dict, index: int = 1) -> dict:
    """Format a retrieved document into a comprehensive source item with visible file names."""
    meta = doc.get("metadata", {}) or {}
    source_file = (
        doc.get("source_file")
        or meta.get("source_file")
        or ("web_search" if meta.get("is_live") else "knowledge_base.json")
    )
    url = meta.get("url") or doc.get("url") or meta.get("doc_url") or doc.get("doc_url") or ""

    # Clean display file name
    file_name = source_file
    if source_file in ("_structured_faculty", "faculty"):
        file_name = "faculty.json"
    elif source_file in ("_structured_fee", "fee"):
        file_name = "fee_structures.json"
    elif source_file in ("_structured_principal", "_structured_fdp"):
        file_name = "external_facts.json"
    elif source_file in ("_structured_admission", "admission"):
        file_name = "admission_process.json"
    elif source_file in ("_structured_courses", "courses"):
        file_name = "courses_offered.json"
    elif source_file == "web_search":
        file_name = "Live Web (gndec.ac.in)"
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                file_name = f"web: {parsed.netloc}{parsed.path[:30]}"
            except Exception:
                file_name = "Live Web (gndec.ac.in)"
    elif "/" in source_file and not source_file.startswith("http"):
        file_name = source_file.split("/")[-1]
    elif not file_name or file_name == "unknown":
        file_name = "knowledge_base.json"

    question = (
        doc.get("question")
        or meta.get("question")
        or meta.get("title")
        or doc.get("title")
        or ""
    )
    section = doc.get("section") or meta.get("section") or ""
    doc_url = url or (f"https://{source_file}" if source_file and not source_file.endswith(".json") and "." in source_file else "")

    return {
        "index": index,
        "source_file": source_file,
        "file_name": file_name,
        "question": question,
        "section": section,
        "doc_url": doc_url,
        "content": doc.get("content", "")[:500],
        "metadata": meta,
    }


def _get_memory(phone: str, session_id: str) -> ConversationBufferWindowMemory:
    """Retrieve or create a ConversationBufferWindowMemory for the session."""
    key = f"{phone}:{session_id}"
    if key not in _memory_store:
        try:
            history = RedisChatMessageHistory(
                session_id=key,
                url=REDIS_URL,
                ttl=SESSION_TTL,
            )
        except Exception as e:
            logging.warning(f"Redis unavailable, using in-memory history: {e}")
            history = ChatMessageHistory()
        _memory_store[key] = ConversationBufferWindowMemory(
            k=10,
            chat_memory=history,
            return_messages=True,
            memory_key="chat_history",
            input_key="input",
        )
    return _memory_store[key]


# --- Helper functions for backward compatibility ---

async def check_toxicity(text: str) -> Tuple[bool, str]:
    """Simple rule-based toxicity check (legacy)."""
    toxic_patterns = [
        r"\b(hate|stupid|idiot|dumb|fuck|shit|bitch|asshole|bastard|nigger|faggot|retard|kill yourself|kys|go die)\b",
    ]
    for pattern in toxic_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, "Content violates safety guidelines"
    return False, ""


async def detect_followup(query: str, phone: str, session_id: str) -> dict:
    """Detect if a query is a follow-up to a previous query."""
    memory = _get_memory(phone, session_id)
    chat_history = memory.chat_memory.messages

    if not chat_history:
        return {"is_followup": False, "previous_query": "", "context": ""}

    user_messages = [msg for msg in chat_history if msg.type == "human"]
    if not user_messages:
        return {"is_followup": False, "previous_query": "", "context": ""}

    last_query = user_messages[-1].content

    followup_indicators = [
        "what about", "how about", "and", "also", "more", "else", "other",
        "tell me more", "details", "specific", "expand", "elaborate",
        "who else", "what else", "where else", "when else",
        "it", "this", "that", "these", "those", "its", "their",
    ]

    query_lower = query.lower()
    is_followup = any(indicator in query_lower for indicator in followup_indicators)

    return {
        "is_followup": is_followup,
        "previous_query": last_query if is_followup else "",
        "context": last_query if is_followup else ""
    }


def is_direct_fee_query(query: str, sources: List[dict]) -> bool:
    """Check if query is a direct fee query that can be answered from structured data."""
    fee_keywords = ["fee", "fees", "cost", "tuition", "charges", "price"]
    query_lower = query.lower()

    has_fee_keyword = any(kw in query_lower for kw in fee_keywords)
    has_structured_fee = any(s.get("source_file") == "_structured_fee" for s in sources)

    return has_fee_keyword and has_structured_fee


def is_direct_faculty_query(query: str, sources: List[dict]) -> bool:
    """Check if query is a direct faculty query that can be answered from structured data."""
    faculty_keywords = ["faculty", "professor", "teacher", "hod", "head of department", "staff"]
    query_lower = query.lower()

    has_faculty_keyword = any(kw in query_lower for kw in faculty_keywords)
    has_structured_faculty = any(s.get("source_file") == "_structured_faculty" for s in sources)

    return has_faculty_keyword and has_structured_faculty


def build_direct_fee_response(sources: List[dict], lang: str) -> str:
    """Build a direct response from structured fee data."""
    fee_sources = [s for s in sources if s.get("source_file") == "_structured_fee"]
    if not fee_sources:
        return "I do not have specific fee information available."

    parts = ["**GNDEC Fee Structure**\n"]
    for src in fee_sources:
        answer = src.get("answer", "")
        question = src.get("question", "")
        if answer:
            parts.append(f"**{question}**\n{answer}\n")

    return "\n".join(parts)


def build_direct_faculty_response(sources: List[dict], lang: str) -> str:
    """Build a direct response from structured faculty data."""
    faculty_sources = [s for s in sources if s.get("source_file") == "_structured_faculty"]
    if not faculty_sources:
        return "I do not have specific faculty information available."

    parts = ["**GNDEC Faculty Information**\n"]
    for src in faculty_sources:
        answer = src.get("answer", "")
        question = src.get("question", "")
        if answer:
            parts.append(f"**{question}**\n{answer}\n")

    return "\n".join(parts)


async def build_prompt(query: str, phone: str, session_id: str, lang: str) -> Tuple[str, List[dict], ConversationBufferWindowMemory]:
    """Build the RAG prompt with context and memory (legacy function for backward compat)."""
    memory = _get_memory(phone, session_id)

    # Get conversation history
    history = memory.chat_memory.messages[-10:]  # Last 10 messages
    history_str = "\n".join([
        f"User: {msg.content}" if msg.type == "human" else f"Assistant: {msg.content}"
        for msg in history
    ])

    # Get retrieval context
    from .vectorstore import get_retriever
    retriever = get_retriever()
    docs = await asyncio.to_thread(retriever, query)

    sources = []
    context_parts = []
    for i, doc in enumerate(docs, 1):
        if hasattr(doc, 'page_content'):
            content = doc.page_content
            metadata = doc.metadata
        elif isinstance(doc, dict):
            content = doc.get("content", doc.get("page_content", ""))
            metadata = doc.get("metadata", {})
        else:
            content = str(doc)
            metadata = {}

        context_parts.append(f"[{i}] {content}")
        sources.append({
            "source_file": metadata.get("source", "unknown"),
            "content": content[:500],
            "metadata": metadata,
        })

    context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

    # Build prompt
    prompt = f"""You are the official GNDEC (Guru Nanak Dev Engineering College, Ludhiana) information assistant.

MANDATORY RULES:
1. Answer ONLY using the provided GNDEC knowledge context. NEVER use external knowledge.
2. NO conversational filler, greetings, or pleasantries. Start directly with the factual answer.
3. Be comprehensive: include all specific details, facilities, statistics, numbers, library volumes, hostel amenities, course outlines, and contact numbers present in the context.
4. If asked for a list of courses/programs, provide a clean bulleted list of the program/branch names.
5. NO GENERAL KNOWLEDGE OR CODING: If asked to write code or solve homework, refuse: "I can't answer this, I only have knowledge about GNDEC college."
6. INSTITUTIONAL IDENTITY: You are exclusively the assistant for Guru Nanak Dev Engineering College (GNDEC), Ludhiana. You MUST REFUSE queries about other institutions or colleges named after Guru Nanak Dev (including GNDU Amritsar, GNDPC Ludhiana, GNDIT Delhi, GNIET Nagpur, GNIT, Sri Guru Nanak Dev Khalsa College, Guru Nanak Khalsa College, etc.) and clarify that you only serve GNDEC Ludhiana.
7. Cite sources inline using brackets based on the document numbers provided in context (e.g., [1]).
8. If the retrieved knowledge does not contain the answer, state: "I do not have information about that." and suggest checking gndec.ac.in.
9. NEVER generate offensive or discriminatory language.
10. DO NOT mix multiple languages in a single response.

Tone: Direct, factual, precise, and professional.

Conversation History:
{history_str if history_str else "No previous conversation."}

Context Documents:
{context}

User Query: {query}

Answer:"""

    return prompt, sources, memory


# --- Main API functions (refactored to use RAG pipeline) ---

async def answer_sync(query: str, phone: str, session_id: str, lang: str = "auto") -> Dict[str, Any]:
    """
    Synchronous answer endpoint - now uses the unified RAG pipeline.

    Returns: {"answer": str, "sources": List[dict], "cached": bool, "verification_status": str}
    """
    try:
        # Run the RAG pipeline
        ctx = await answer_query(query, phone, session_id, lang)

        # Convert pipeline context to legacy response format
        if ctx.errors:
            return {
                "answer": "I'm experiencing technical difficulties. Please try again.",
                "sources": [],
                "cached": False,
                "error": ctx.errors[-1] if ctx.errors else "Unknown error"
            }

        answer = ""
        if ctx.generation and ctx.generation.answer:
            answer = ctx.generation.answer

        sources = []
        verification_status = "unknown"

        if ctx.retrieval and ctx.retrieval.combined_documents:
            sources = [
                format_source_item(doc, i + 1)
                for i, doc in enumerate(ctx.retrieval.combined_documents)
            ]
        elif ctx.generation and ctx.generation.citations:
            sources = [
                format_source_item(doc, i + 1)
                for i, doc in enumerate(ctx.generation.citations)
            ]

        if ctx.verification:
            verification_status = ctx.verification.status.value if hasattr(ctx.verification.status, 'value') else str(ctx.verification.status)

        # Check if cached (based on pipeline metadata)
        cached = ctx.metadata.get("cached", False) if ctx.metadata else False

        return {
            "answer": answer,
            "sources": sources,
            "cached": cached,
            "verification_status": verification_status,
            "request_id": ctx.request_id,
        }

    except Exception as e:
        logging.exception(f"answer_sync failed for query: {query}")
        return {
            "answer": "I'm experiencing technical difficulties. Please try again.",
            "sources": [],
            "cached": False,
            "error": str(e)
        }


async def answer_stream(query: str, phone: str, session_id: str, lang: str = "auto") -> AsyncGenerator[str, None]:
    """
    Streaming answer endpoint - uses RAG pipeline for retrieval/generation,
    then streams the answer with verification.
    """
    # Input validation
    if not query or not query.strip():
        yield json.dumps({"type": "blocked", "message": "Empty query"}) + "\n"
        return

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

    # Run RAG pipeline (non-streaming internally, then stream output)
    try:
        ctx = await answer_query(query, phone, session_id, lang)

        # Send sources first
        sources = []
        if ctx.retrieval and ctx.retrieval.combined_documents:
            sources = [
                format_source_item(doc, i + 1)
                for i, doc in enumerate(ctx.retrieval.combined_documents)
            ]
        yield json.dumps({"type": "sources", "sources": sources}) + "\n"

        # Stream the answer
        if ctx.generation and ctx.generation.answer:
            answer = ctx.generation.answer
            memory = _get_memory(phone, session_id)

            # Check verification status
            verification_status = "unknown"
            if ctx.verification:
                verification_status = ctx.verification.status.value if hasattr(ctx.verification.status, 'value') else str(ctx.verification.status)

            # Stream in chunks (lines)
            for line in answer.split("\n"):
                yield json.dumps({"type": "content", "delta": line + "\n"}) + "\n"
                await asyncio.sleep(0.002)

            # Save to memory and persistence
            memory.chat_memory.add_user_message(query)
            memory.chat_memory.add_ai_message(answer)
            await save_message(phone, session_id, "user", query)
            await save_message(phone, session_id, "assistant", answer)

            # Add verification metadata at the end
            yield json.dumps({
                "type": "meta",
                "verification_status": verification_status,
                "request_id": ctx.request_id,
            }) + "\n"

            logging.info(f"Stream completed successfully (verification: {verification_status})")
        else:
            yield json.dumps({"type": "content", "delta": "I do not have information about that."}) + "\n"

    except Exception as e:
        logging.exception(f"answer_stream failed for query: {query}")
        yield json.dumps({"type": "error", "message": "I'm experiencing technical difficulties. Please try again."}) + "\n"


async def clear_redis_session(phone: str, session_ids: Iterable[str]) -> bool:
    """Clears Redis chat history for given session IDs (legacy function)."""
    if not session_ids:
        logging.warning("[clear_redis_session] ⚠️ No session IDs provided")
        return False

    session_ids = list(session_ids)
    logging.info(f"[clear_redis_session] Clearing Redis for {len(session_ids)} session(s)")

    cleared_count = 0
    for session_id in session_ids:
        key = f"{phone}:{session_id}"

        # Clear from local memory store
        if key in _memory_store:
            _memory_store[key].chat_memory.clear()
            del _memory_store[key]
            logging.info(f"[clear_redis_session] Cleared local memory for {key}")
            cleared_count += 1

        # Try to clear from Redis
        try:
            history = RedisChatMessageHistory(
                session_id=key,
                url=REDIS_URL,
                ttl=SESSION_TTL,
            )
            history.clear()
            logging.info(f"[clear_redis_session] Cleared Redis for {key}")
            cleared_count += 1
        except Exception as e:
            logging.warning(f"[clear_redis_session] Failed to clear Redis for {key}: {e}")

    return cleared_count > 0
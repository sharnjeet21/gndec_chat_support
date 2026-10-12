"""
Generation stage - calls LLM with accumulated context to produce answer.
"""

from __future__ import annotations
import logging
import time
from typing import Any

from .contracts import GenerationInput, GenerationOutput

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the official GNDEC (Guru Nanak Dev Engineering College, Ludhiana) information assistant.

MANDATORY RULES:
1. Answer using the provided GNDEC knowledge context below. You have TWO types of sources:
   - [WEB] / [WEB-ANSWER] / [WEB-KNOWLEDGE] = LIVE data fetched right now from gndec.ac.in (most current — PRIORITISE these for recent info)
   - All other sources = Indexed knowledge base (comprehensive structured data)
2. When LIVE web results and indexed data disagree, ALWAYS trust the LIVE web result — it is more current.
3. NO conversational filler, greetings, or pleasantries. Start directly with the factual answer.
4. Be comprehensive: include all specific details, numbers, fees, hostel amenities, contact numbers present in the context.
5. If asked for a list of courses/programs, provide a clean bulleted list of the program/branch names.
6. NO GENERAL KNOWLEDGE OR CODING: If asked to write code or solve homework, refuse: "I can't answer this, I only have knowledge about GNDEC college."
7. Cite sources inline using brackets with the document number and file name (e.g., [1: Fee_Structure.php], [2: admission_process.json], [WEB: gndec.ac.in]).
8. If neither the indexed knowledge nor the live web results contain the answer, state: "I do not have information about that." and suggest checking gndec.ac.in.
9. NEVER generate offensive or discriminatory language.
10. DO NOT mix multiple languages in a single response.
11. ALWAYS provide the maximum amount of detail possible. Act like an expert counselor giving a complete breakdown.

Tone: Warm, highly detailed, exhaustive, and helpful. Use Markdown for clarity."""


async def generate(input_: GenerationInput) -> GenerationOutput:
    """
    Generate answer using LLM with provided context.

    Builds context from both indexed FAISS docs and live SerpAPI web results,
    clearly labelling each so the LLM knows which source is more current.
    """
    from ..llm.llm import call_model_async

    start_time = time.time()

    # Split docs into indexed knowledge vs live web results
    indexed_parts: list[str] = []
    web_parts: list[str] = []
    citations: list[dict] = []

    doc_index = 1
    for doc in input_.retrieval_output.combined_documents:
        content = doc.get("content", "").strip()
        if not content:
            continue

        source_file = doc.get("source_file", "unknown")
        metadata = doc.get("metadata", {})
        is_live = metadata.get("is_live", False) or source_file == "web_search"
        url = metadata.get("url", "")

        label = f"[{doc_index}]"
        clean_name = source_file
        if source_file in ("_structured_faculty", "faculty"):
            clean_name = "faculty.json"
        elif source_file in ("_structured_fee", "fee"):
            clean_name = "fee_structures.json"
        elif source_file in ("_structured_principal", "_structured_fdp"):
            clean_name = "external_facts.json"
        elif source_file in ("_structured_admission", "admission"):
            clean_name = "admission_process.json"
        elif source_file in ("_structured_courses", "courses"):
            clean_name = "courses_offered.json"
        elif clean_name == "web_search" or is_live:
            clean_name = "gndec.ac.in (Live Web)"
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    clean_name = f"{parsed.netloc}{parsed.path[:25]}"
                except Exception:
                    clean_name = "gndec.ac.in"
        elif "/" in clean_name and not clean_name.startswith("http"):
            clean_name = clean_name.split("/")[-1]

        if is_live:
            source_label = f"LIVE Web ({url})" if url else "LIVE Web (gndec.ac.in)"
            web_parts.append(f"{label} [File: {clean_name}]\n{content}\n   Source: {source_label}")
        else:
            indexed_parts.append(f"{label} [File: {clean_name}]\n{content}\n   Source File: {clean_name}")

        citations.append({
            "index": doc_index,
            "content_preview": content[:200],
            "source_file": source_file,
            "file_name": clean_name,
            "metadata": metadata,
            "is_live": is_live,
        })
        doc_index += 1

    # Build the context block — live results first (so LLM sees them with highest priority)
    context_sections: list[str] = []
    if web_parts:
        context_sections.append(
            "--- LIVE WEB RESULTS (from gndec.ac.in right now — highest priority) ---\n"
            + "\n\n".join(web_parts)
        )
    if indexed_parts:
        context_sections.append(
            "--- INDEXED KNOWLEDGE BASE (comprehensive structured data) ---\n"
            + "\n\n".join(indexed_parts)
        )

    context_text = "\n\n".join(context_sections) if context_sections else "No relevant documents found."

    # Build conversation history
    history_text = ""
    if input_.conversation_history:
        history_lines = [f"{m['type']}: {m['content']}" for m in input_.conversation_history[-10:]]
        history_text = "\n".join(history_lines)
    else:
        history_text = "No prior conversation."

    # Language rule
    lang_rules = {
        "en": "Answer entirely in English.",
        "en-IN": "Answer entirely in English.",
        "hi-IN": "Answer entirely in Hindi (Devanagari script).",
        "pa-IN": "Answer entirely in Punjabi (Gurmukhi script).",
    }
    lang_rule = lang_rules.get(input_.language, "Answer entirely in English.")

    # Build final prompt
    prompt = f"""{SYSTEM_PROMPT}

Conversation history (last 10 messages):
{history_text}

Relevant knowledge about GNDEC (use ONLY the relevant parts to build your answer):
{context_text}

User question:
{input_.query}

Instructions:
- Answer the user's question thoroughly, accurately, and exhaustively using the provided knowledge.
- ADMISSION & QUOTA QUERIES: If the user asks about admissions, eligibility, B.Tech, or quotas, ALWAYS explain the relevant quotas and reservations present in the context, including the **70% Rural Quota** (70% seats reserved for rural Punjab students who passed 10th and 12th from rural schools), **85% Punjab Quota**, **15% Other States Quota**, **50% Sikh Minority Quota**, **Tuition Fee Waiver (TFW)**, and **Post Matric Scholarship (PMS)**!
- WHEN explicitly asked for fee structures:
  * YOU MUST generate a complete, separate Markdown table for EACH individual course/program present in the context (e.g., B.Tech., MBA/MCA, M.Tech., BBA/BCA, B.VoC., B.Arch., B.Com., B.Tech. Lateral Entry).
  * NEVER summarize, skip, or truncate any table or semester row. Output all semesters completely.
  * Each table MUST use the EXACT following 14-column format to match the official admission portal:
| Sr No. | Program | Semester | Hostel (Boys) | Hostel (Girls) | PMS (Total) | PMS (Hostel Boys) | PMS (Hostel Girls) | TFW (Total) | TFW (Hostel Boys) | TFW (Hostel Girls) | Gen (Total) | Gen (Hostel Boys) | Gen (Hostel Girls) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  * Fill the rows with data from the knowledge context. Leave cells blank if data is missing.
- COURSE QUERIES: If the user asks for a list of courses/programs (e.g., "What B.Tech courses are offered?"):
  * Provide a clean, structured bulleted list of the programs and branches.
  * STRIP OUT and NEVER output any internal syllabus scheme codes, classroom numbers, or subject lists.
- Dynamically choose the best Markdown formatting for other data: bulleted lists for criteria/features, numbered lists for steps.
- Check conversation history for context on follow-up questions.
- STRICTLY DO NOT GUESS OR HALLUCINATE. If the answer is not in the provided knowledge, say "I do not have information about that." and suggest visiting gndec.ac.in.
- Do NOT use irrelevant knowledge.
- Use standard Markdown format for tables, bold text, bullet points, etc. to organize information clearly.
- Format numbers clearly with spaces (e.g. "Rs. 50,000" not "Rs50000").
- CITATIONS & SOURCE FILE NAMES:
  * When referencing information in your answer, cite the source file and number inline using brackets (e.g., [1: fee_structures.json], [2: faculty.json], [3: gndec.ac.in], or [4: admission_process.json]). NEVER write bare [1], [2] without the file name!
  * At the very end of your response, ALWAYS include a "### Sources" section listing every referenced file and title:
    ### Sources
    - [1] `fee_structures.json` — B.Tech Fee Structure
    - [2] `faculty.json` — Information Technology Faculty
    - [3] `gndec.ac.in` — Official Website
- STRICT SINGLE-LANGUAGE RULE: Answer entirely in ONE language (the exact language the user typed). NEVER mix languages.
- Give your answer directly. No chain of thought, no thinking process, no <think> tags, no preamble.

Answer:"""

    try:
        answer = await call_model_async(prompt=prompt)
        latency_ms = int((time.time() - start_time) * 1000)

        return GenerationOutput(
            answer=answer.strip(),
            citations=citations,
            model="gpt-4o-mini",  # Default model
            tokens_used=0,  # Not tracked by current LLM wrapper
            latency_ms=latency_ms,
            metadata={
                "context_docs": len(input_.retrieval_output.combined_documents),
                "prompt_chars": len(prompt),
            },
        )
    except Exception as e:
        logger.error(f"[Generation] LLM call failed: {e}")
        latency_ms = int((time.time() - start_time) * 1000)
        return GenerationOutput(
            answer="I'm experiencing technical difficulties. Please try again.",
            citations=[],
            model="error",
            tokens_used=0,
            latency_ms=latency_ms,
            metadata={"error": str(e)},
        )
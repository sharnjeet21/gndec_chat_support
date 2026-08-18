import re

with open("backend/agent.py", "r") as f:
    content = f.read()

# Add get_hardcoded_fees function before answer_sync
helper_func = """
def get_hardcoded_fees():
    import json
    import os
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "fee_structures.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = ["Here are the detailed fee structures for the programs at GNDEC:\\n"]
        for item in data:
            if "answer" in item:
                out.append(item["answer"])
        out.append("\\nWhich specific program are you interested in?")
        return "\\n\\n".join(out)
    except Exception as e:
        return "Fee structure data is currently unavailable."

# ============================
# SYNC RESPONSE (NON-STREAM)
"""

content = content.replace("# ============================\n# SYNC RESPONSE (NON-STREAM)", helper_func)

# Modify answer_sync
sync_hook = """
    if await asyncio.to_thread(is_out_of_domain, query):
        memory.chat_memory.add_ai_message(OOD_TEXT)
        await save_message(phone, session_id, "assistant", OOD_TEXT)
        return {"answer": OOD_TEXT, "sources": []}

    # === HARDCODED FEE INTERCEPTION ===
    if "fee" in query.lower():
        final = get_hardcoded_fees()
        sources = [{"doc_url": "https://admission.gndec.ac.in/Fee_Structure.php", "source_file": "admission.gndec.ac.in/Fee_Structure.php"}]
        memory.chat_memory.add_user_message(query)
        await save_message(phone, session_id, "user", query)
        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        return {"answer": final, "sources": sources}
    # ====================================
"""

content = re.sub(
    r'    if await asyncio\.to_thread\(is_out_of_domain, query\):.*?(?=\n    # Build prompt with RAG context)',
    sync_hook.strip('\n'),
    content,
    flags=re.DOTALL
)

# Modify answer_stream
stream_hook = """
    if await asyncio.to_thread(is_out_of_domain, query):
        yield json.dumps({"type": "blocked", "message": OOD_TEXT}) + "\\n"
        return

    # === HARDCODED FEE INTERCEPTION ===
    if "fee" in query.lower():
        final = get_hardcoded_fees()
        sources = [{"doc_url": "https://admission.gndec.ac.in/Fee_Structure.php", "source_file": "admission.gndec.ac.in/Fee_Structure.php"}]
        memory.chat_memory.add_user_message(query)
        await save_message(phone, session_id, "user", query)
        
        yield json.dumps({"type": "sources", "sources": sources}) + "\\n"
        
        chunk_size = 50
        for i in range(0, len(final), chunk_size):
            yield json.dumps({"type": "content", "delta": final[i:i+chunk_size]}) + "\\n"
            await asyncio.sleep(0.01)
            
        memory.chat_memory.add_ai_message(final)
        await save_message(phone, session_id, "assistant", final)
        return
    # ====================================
"""

content = re.sub(
    r'    if await asyncio\.to_thread\(is_out_of_domain, query\):.*?(?=\n    prompt, sources, memory = await build_prompt)',
    stream_hook.strip('\n'),
    content,
    flags=re.DOTALL
)

with open("backend/agent.py", "w") as f:
    f.write(content)

print("Updated agent.py with hardcoded fee logic")

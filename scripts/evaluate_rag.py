import asyncio
import json
import time
import os
import sys

# Ensure the root directory is in the python path to allow 'backend' to act as a package
sys.path.append(os.getcwd())

import backend.agent
# Bypass the Domain Guard strictly for this evaluation script!
backend.agent.is_out_of_domain = lambda q: False

from backend.agent import answer_sync

INPUT_FILE = "data/500000_rag_questions.txt"
OUTPUT_FILE = "data/rag_evaluation_results.txt"
CONCURRENCY_LIMIT = 5  # Limits simultaneous active requests
MAX_QUESTIONS_TO_TEST = None  # None means test ALL questions
BATCH_SIZE = 1000 # Read and process in batches to save RAM

async def evaluate_question(query: str, phone="eval_script", session_id="eval_session"):
    try:
        start_time = time.time()
        response = await answer_sync(query=query, phone=phone, session_id=session_id)
        end_time = time.time()
        
        result = {
            "question": query,
            "answer": response.get("answer", ""),
            "sources_retrieved": len(response.get("sources", [])),
            "latency_seconds": round(end_time - start_time, 2),
            "status": "success"
        }
    except Exception as e:
        result = {
            "question": query,
            "answer": "",
            "sources_retrieved": 0,
            "latency_seconds": 0.0,
            "status": f"error: {str(e)}"
        }
    return result

async def worker(queue: asyncio.Queue, out_f, progress_dict):
    while True:
        query = await queue.get()
        if query is None:
            break
            
        res = await evaluate_question(query)
        
        # Write sequentially to TXT file, instantly flushing to disk
        # (Since multiple workers might write, we format as a single string to avoid interleaving lines)
        output_block = (
            f"Q: {res['question']}\n"
            f"A: {res['answer']}\n"
            f"[Sources: {res['sources_retrieved']} | Latency: {res['latency_seconds']}s | Status: {res['status']}]\n"
            f"{'-' * 80}\n"
        )
        out_f.write(output_block)
        out_f.flush()
        
        progress_dict["completed"] += 1
        total_overall = progress_dict["previously_done"] + progress_dict["completed"]
        
        if progress_dict["completed"] % 10 == 0:
            print(f"Progress: {progress_dict['completed']} newly completed. (Total overall: {total_overall})")
            
        queue.task_done()

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # 1. Track processed questions using a memory-efficient set
    processed_questions = set()
    if os.path.exists(OUTPUT_FILE):
        print(f"Found existing {OUTPUT_FILE}. Loading processed questions to resume...")
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                if line.startswith("Q: "):
                    processed_questions.add(line.strip()[3:])
        print(f"Loaded {len(processed_questions)} already completed questions.")

    progress_dict = {"completed": 0, "previously_done": len(processed_questions)}
    
    # 2. Setup Queue and Workers
    queue = asyncio.Queue(maxsize=CONCURRENCY_LIMIT * 2)
    out_f = open(OUTPUT_FILE, "a")
    
    workers = []
    for _ in range(CONCURRENCY_LIMIT):
        task = asyncio.create_task(worker(queue, out_f, progress_dict))
        workers.append(task)
        
    print(f"Starting evaluation with concurrency {CONCURRENCY_LIMIT}. Loading file incrementally to save RAM...")

    # 3. Read file lazily (generator) to avoid loading 500k strings into RAM
    # We also keep track of what we added to avoid duplicates in the same file
    seen_in_this_run = set()
    added_count = 0
    
    with open(INPUT_FILE, "r") as f:
        for line in f:
            q = line.strip()
            if not q:
                continue
            if q in processed_questions or q in seen_in_this_run:
                continue
                
            seen_in_this_run.add(q)
            
            # This will block if the queue is full, preventing RAM buildup!
            await queue.put(q)
            added_count += 1
            
            if MAX_QUESTIONS_TO_TEST and added_count >= MAX_QUESTIONS_TO_TEST:
                break
                
    # 4. Signal workers to stop
    for _ in range(CONCURRENCY_LIMIT):
        await queue.put(None)
        
    # Wait for all processing to finish
    await asyncio.gather(*workers)
    
    out_f.close()
    print(f"Evaluation finished! Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

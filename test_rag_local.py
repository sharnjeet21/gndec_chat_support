import asyncio
import os
import sys

# Setup environment variables so the local agent works
os.environ["API_KEY"] = "naman@1234"

from backend.agent import answer_sync

async def main():
    questions = [
        "What is the B.Tech fee structure?",
        "Are there any seats reserved for rural or Sikh minority students?",
        "What are the cutoff ranks for B.Tech admission?"
    ]
    
    for q in questions:
        print(f"\n--- QUERY: {q} ---")
        try:
            res = await answer_sync(q, "testphone", "testsession")
            print(res.get('answer'))
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())

import sys
import os

# Add backend dir to path if needed or just run from project root
sys.path.append(os.path.join(os.getcwd(), "backend"))

from agent import answer_sync

queries = [
    "What is the B.Tech fee structure?",
    "Are there any seats reserved for rural or Sikh minority students?",
    "What are the cutoff ranks for B.Tech admission?"
]

for q in queries:
    print(f"\n--- QUERY: {q} ---")
    response, _, _ = answer_sync(q, [])
    print(response)


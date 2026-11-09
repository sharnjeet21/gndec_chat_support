import requests
import json
import time

api_key = "naman@1234"
session_url = "http://localhost:8000/api/start_session?phone=1234567890"
ask_url = "http://localhost:8000/api/ask"
headers = {"X-API-KEY": api_key}

def test_rag(query):
    try:
        # 1. Start Session
        res = requests.get(session_url, headers=headers, timeout=20)
        session_id = res.json().get("session_id")
        
        # 2. Ask question
        payload = {"phone": "1234567890", "session_id": session_id, "q": query}
        print(f"\nQ: {query}")
        start = time.time()
        res = requests.post(ask_url, headers=headers, json=payload, timeout=60)
        
        if res.status_code == 200:
            print(f"A: {res.json().get('response')}")
        else:
            print(f"Error {res.status_code}: {res.text}")
        print(f"Took: {time.time() - start:.2f}s")
            
    except Exception as e:
        print(f"Error for '{query}': {e}")

test_rag("Which types of plants or tree species does GNDEC have in its campus? Can you name those species?")

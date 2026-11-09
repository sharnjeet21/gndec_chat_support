import requests
import json
import urllib.parse

def ask_bot(question):
    headers = {"X-API-KEY": "naman@1234"}
    
    # Start session first
    session_url = "http://localhost:8000/api/start_session?phone=12345&session_id=test_session_tree"
    requests.get(session_url, headers=headers, timeout=10)
    
    url = f"http://localhost:8000/api/ask?phone=12345&session_id=test_session_tree&q={urllib.parse.quote(question)}"
    try:
        response = requests.get(url, headers=headers, timeout=3000)
        if response.status_code == 200:
            print(f"Q: {question}\nA: {response.json().get('answer')}\n")
        else:
            print(f"Error for '{question}': {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        print(f"Error for '{question}': Request timed out")
    except Exception as e:
        print(f"Error for '{question}': {e}")

questions = [
    "Are there any plants or trees at GNDEC?",
    "can you name those species",
    "Who is Akshay Girdhar? What is his designation and email?",
    "Search the live GNDEC website and tell me the very latest news or circular posted there recently."
]

for q in questions:
    ask_bot(q)

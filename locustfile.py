"""
GNDEC Chatbot — Load Test
Run: locust -f locustfile.py --host=http://localhost:8080
"""
import random
from locust import HttpUser, task, between

PHONE = "9877803978"
SESSIONS = ["test1", "test2", "test3"]

QUESTIONS = [
    "What B.Tech programs does GNDEC offer?",
    "How do I apply for admission at GNDEC?",
    "What is the fee structure for B.Tech?",
    "Tell me about the CSE department",
    "What are the hostel facilities at GNDEC?",
    "What scholarships are available at GNDEC?",
    "What is the placement record of GNDEC?",
    "Tell me about the ECE department",
    "What is the admission process for MBA?",
    "What are the NCC activities at GNDEC?",
    "Who are the notable alumni of GNDEC?",
    "What is the rural area quota at GNDEC?",
    "What is the NAAC accreditation status of GNDEC?",
    "What are the library facilities at GNDEC?",
    "How to check results at GNDEC?",
]


class GNDECUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def ask_question(self):
        q = random.choice(QUESTIONS)
        session_id = random.choice(SESSIONS)

        self.client.get(
            "/api/ask",
            params={"phone": PHONE, "session_id": session_id, "q": q},
            headers={"X-API-KEY": "naman@1234"},
            name="ASK Sync",
        )

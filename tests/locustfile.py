import csv
import random
from locust import HttpUser, task, between

PHONE = "9877803978"
SESSIONS = ["test1", "test2", "test3"]

# Load Customer Questions once
CSV_PATH = "./data/nebero_data.csv"
QUESTIONS = []

with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        q = row.get("Customer Question", "").strip()
        if q:
            QUESTIONS.append(q)

if not QUESTIONS:
    raise ValueError("No customer questions found in nebero_data.csv!")

print(f"Loaded {len(QUESTIONS)} questions from CSV.")


class SupportUser(HttpUser):
    wait_time = between(1, 2)  # wait 1–2 seconds between hits

    @task
    def ask_question(self):
        q = random.choice(QUESTIONS)
        session_id = random.choice(SESSIONS)

        self.client.get(
            "/api/ask",
            params={"phone": PHONE, "session_id": session_id, "q": q},
            name="ASK Sync",
        )

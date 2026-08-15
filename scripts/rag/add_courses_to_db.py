import json
import asyncio
from backend.vectorstore import add_documents

async def embed_courses():
    with open("data/courses_offered.json", "r") as f:
        data = json.load(f)
    await add_documents(data)
    print("Embedded courses successfully.")

if __name__ == "__main__":
    asyncio.run(embed_courses())

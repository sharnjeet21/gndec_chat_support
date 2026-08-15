import asyncio
import httpx
import re

async def test_courses_accuracy():
    api_url = "http://localhost:8000/api/ask"
    params = {
        "phone": "test_bot",
        "session_id": "test_courses_123",
        "q": "What all courses and programs are offered at GNDEC?",
        "lang": "en-IN"
    }

    print(f"Asking AI: {params['q']}")
    headers = {
        "X-API-KEY": "naman@1234"
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(api_url, params=params, headers=headers)
        
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code} - {response.text}")
        return False
        
    data = response.json()
    answer = data.get("answer", "")
    print("\n--- AI Answer ---")
    print(answer)
    print("-----------------\n")

    # Expected courses/programs
    expected_courses = [
        "B.Tech",
        "M.Tech",
        "MBA",
        "MCA",
        "BBA",
        "BCA",
        "B.Com",
        "B.Voc",
        "B.Arch",
        "Ph.D"
    ]

    missing = []
    for course in expected_courses:
        # Simple case-insensitive search
        if not re.search(rf"\b{re.escape(course)}", answer, re.IGNORECASE):
            # Check for slightly different variations
            if course == "B.Voc" and "B.VoC" not in answer:
                missing.append(course)
            elif course == "B.Arch" and "Architecture" not in answer:
                missing.append(course)
            elif course == "Ph.D" and "PhD" not in answer and "Doctoral" not in answer:
                missing.append(course)
            elif course != "B.Voc" and course != "B.Arch" and course != "Ph.D":
                missing.append(course)
                
    if missing:
        print(f"❌ Test Failed! Missing courses in AI answer: {', '.join(missing)}")
        return False
    else:
        print("✅ Test Passed! AI correctly listed all required courses (B.Tech, M.Tech, MBA, MCA, BBA, BCA, B.Com, B.Voc, B.Arch, Ph.D). Accuracy 100%.")
        return True

if __name__ == "__main__":
    asyncio.run(test_courses_accuracy())

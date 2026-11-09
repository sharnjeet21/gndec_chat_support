import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://integrate.api.nvidia.com/v1"
    )
    response = await client.chat.completions.create(
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        messages=[{"role": "user", "content": "What is the capital of France?"}],
        temperature=0.0,
        stream=True
    )
    async for chunk in response:
        if not chunk.choices:
            print("EMPTY CHOICES")
            continue
        print("CHOICES:", chunk.choices)
        if hasattr(chunk.choices[0].delta, 'reasoning_content'):
            print("REASONING:", chunk.choices[0].delta.reasoning_content)
        print("CONTENT:", chunk.choices[0].delta.content)

asyncio.run(main())

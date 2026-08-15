import os, asyncio
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="nvidia/nemotron-3.5-lightning-30b-a3b",
    api_key=os.environ.get("OPENAI_API_KEY", "***REMOVED_NVIDIA_KEY_1***"),
    base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.0
)

async def main():
    async for chunk in llm.astream("Hi"):
        print(repr(chunk))
        break

asyncio.run(main())

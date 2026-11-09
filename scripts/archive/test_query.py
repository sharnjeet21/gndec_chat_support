import asyncio
import os
import sys

from backend.agent import answer_sync

async def main():
    res = await answer_sync("give me detailed fee structure", "12345", "test_session")
    print(res["answer"])

if __name__ == "__main__":
    asyncio.run(main())

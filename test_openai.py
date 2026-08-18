import os
from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "***REMOVED_NVIDIA_KEY_2***"
)

completion = client.chat.completions.create(
  model="meta/llama-guard-4-12b",
  messages=[{"role":"user","content":"I forgot how to kill a process in Linux, can you help?"}],
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

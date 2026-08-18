import requests

text = "I forgot how to kill a process in Linux, can you help?"

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "Authorization": "Bearer ***REMOVED_NVIDIA_KEY_2***",
    "Accept": "application/json",
}

payload = {
  "messages": [
    {
      "role": "user",
      "content": text
    }
  ],
  "model": "meta/llama-guard-4-12b",
  "max_tokens": 20,
  "temperature": 0.2,
  "top_p": 0.7,
}

response = requests.post(invoke_url, headers=headers, json=payload, timeout=10)
print(response.status_code)
print(response.json())

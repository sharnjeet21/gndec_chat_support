import requests

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

headers = {
    "Authorization": "Bearer ***REMOVED_NVIDIA_KEY_2***",
    "Accept": "text/event-stream" if stream else "application/json",
}

payload = {
  "messages": [
    {
      "role": "user",
      "content": "I forgot how to kill a process in Linux, can you help?"
    },
    {
      "role": "assistant",
      "content": "Sure! To kill a process in Linux, you can use the kill command followed by the process ID (PID) of the process you want to terminate."
    }
  ],
  "model": "meta/llama-guard-4-12b",
  "max_tokens": 5,
  "stream": stream,
  "temperature": 0.2,
  "top_p": 0.7,
  "conversation": [
    {
      "id": "3c7dda9f-76d1-442c-979f-7a48d9fef487",
      "label": "Role: User",
      "textAreaContent": "I forgot how to kill a process in Linux, can you help?",
      "imageArray": []
    },
    {
      "id": "67bb0011-4040-44e5-97a3-202efd7ea8d9",
      "label": "Role: Assistant",
      "textAreaContent": "Sure! To kill a process in Linux, you can use the kill command followed by the process ID (PID) of the process you want to terminate.",
      "imageArray": []
    }
  ]
}

try:
    response = requests.post(invoke_url, headers=headers, json=payload, stream=stream, timeout=20)
    print(response.status_code)
    print(response.json())
except Exception as e:
    print("Error:", e)

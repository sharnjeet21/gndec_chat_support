<div align="center">
  <img src="https://gndec.ac.in/sites/default/logo.png" alt="GNDEC Logo" width="150" />
  
  # GNDEC AI Support Agent
  **Intelligent, Multilingual, Voice-Enabled RAG Chatbot for Guru Nanak Dev Engineering College**

  [![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Llama 3](https://img.shields.io/badge/Llama_3-0466C8?style=for-the-badge&logo=meta&logoColor=white)](https://ai.meta.com/llama/)
  [![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)

</div>

## Live Link

[Click here to access the live agent](https://hopefully-someone-initial-roster.trycloudflare.com)

---

## 🚀 Overview

The **GNDEC AI Support Agent** is a state-of-the-art Retrieval-Augmented Generation (RAG) system designed specifically for the students, faculty, and applicants of Guru Nanak Dev Engineering College. 

Built with an **Agentic AI architecture**, it deeply understands college syllabi, fee structures, faculty details, and admission processes. It operates with strict domain guardrails, ensuring that the bot remains highly professional and strictly focused on college matters.

## ✨ Key Features

- 🧠 **Agentic RAG Engine**: Utilizes an Ensemble Retriever combining **FAISS (Semantic)** and **BM25 (Keyword)** with Reciprocal Rank Fusion (RRF) for pinpoint accuracy in retrieving college documents.
- 🗣️ **Multilingual Mastery**: Native, flawless support for **English, Hindi, Punjabi (Gurmukhi & Roman script), and Hinglish**. The LLM is mathematically constrained to perfectly match the user's spoken language.
- 🎙️ **Voice-Enabled (Zero Cost)**: 
  - **Speech-to-Text (Microphone)**: Dictate queries in Punjabi or Hindi effortlessly using the native Web Speech API.
  - **Text-to-Speech (Read Aloud)**: The AI reads its responses aloud using a high-quality, dynamically selected natural Indian accent voice.
- 🛡️ **Ironclad Guardrails**: The LLM runs with zero-tolerance anti-hallucination guardrails and repetition penalties, automatically rejecting non-college queries (like coding or homework help).

---

## 🏗️ Architecture

The system is split into a highly decoupled frontend and backend:

### Backend (Python / FastAPI)
- **Framework**: FastAPI for blazing-fast async endpoints.
- **AI Core**: Llama 3.1 8B Instruct (powered via Ollama / vLLM).
- **Orchestration**: LangChain for chaining tools, prompts, and vector store retrievers.
- **Memory**: Conversation-aware session management.

### Frontend (React / Vite)
- **UI Framework**: React + Tailwind CSS (Glassmorphism design language).
- **Interactivity**: Real-time typing indicators, markdown rendering, and auto-scrolling.
- **Audio Stack**: `window.speechSynthesis` (TTS) and `window.SpeechRecognition` (STT).

---

## 🛠️ Local Setup & Installation

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/sharnjeet21/gndec_chat_support.git
cd gndec_chat_support

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

Open a new terminal window:

```bash
cd support_ui

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
MODEL_PROVIDER=OLLAMA
LLM_MODEL=llama3.1
OPENAI_API_KEY=your_key_here  # If using a cloud LLM provider
```

---

## 🔒 Security & Safety
- **Strict Domain Locking**: The bot will gracefully refuse to answer questions about politics, coding, general knowledge, or anything unrelated to GNDEC.
- **Repetition Collapse Protection**: The LLM configuration is hardened with `presence_penalty` and `frequency_penalty` constraints to prevent hallucination loops when users mix Roman script with regional languages.
- **Rate Limits**: Configured to ensure sustainable hardware usage during traffic spikes.

---

<div align="center">
  <i>Built with ❤️ for Guru Nanak Dev Engineering College</i>
</div>

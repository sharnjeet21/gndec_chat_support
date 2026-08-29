<div align="center">
  <img src="https://gndec.ac.in/sites/default/logo.png" alt="GNDEC Logo" width="150" />
  
  # GNDEC Tech Support Agent
  **Intelligent, Multilingual, Voice-Enabled RAG Chatbot for Guru Nanak Dev Engineering College**

  [![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
  [![Vite](https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E)](https://vitejs.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Llama 3](https://img.shields.io/badge/Llama_3-0466C8?style=for-the-badge&logo=meta&logoColor=white)](https://ai.meta.com/llama/)
  [![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)
  [![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)

  > A highly accurate, AI-powered digital assistant transforming how students, faculty, and applicants interact with Guru Nanak Dev Engineering College data.
</div>

## Live Link

[Click here to access the live agent](https://dealing-price-announces-circular.trycloudflare.com)

---

## 🚀 Overview

The **GNDEC Tech Support Agent** is a state-of-the-art Retrieval-Augmented Generation (RAG) system built with an **Agentic AI architecture**. It deeply understands college syllabi, fee structures, faculty details, and admission processes, seamlessly retrieving and presenting accurate information across multiple languages.

## ✨ Key Features

- 🧠 **Agentic RAG Engine**: Utilizes an Ensemble Retriever combining **FAISS (Semantic)** and **BM25 (Keyword)** with Reciprocal Rank Fusion (RRF) for pinpoint accuracy in retrieving college documents.
- 🗣️ **Multilingual Mastery**: Native, flawless support for **English, Hindi, Punjabi (Gurmukhi & Roman script), and Hinglish**. The LLM perfectly adapts to the user's spoken language.
- 🎙️ **Voice-Enabled (Zero Cost)**: 
  - **Speech-to-Text**: Dictate queries in Punjabi or Hindi effortlessly using the native Web Speech API.
  - **Text-to-Speech**: The AI reads its responses aloud using a dynamically selected, high-quality Indian accent voice.
- 🛡️ **Ironclad Guardrails**: Engineered with zero-tolerance anti-hallucination guardrails to reject non-college queries, ensuring absolute professionalism.

---

## ⚙️ How It Works (Process Flow)

The interaction process is built for speed, safety, and accuracy.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant G as Guardrails
    participant R as RAG System
    participant L as Llama 3.1 LLM

    U->>F: Speak/Type Query (Any Language)
    F->>G: Send Query via API
    G->>G: Check if Query is College-Related
    alt Not College Related
        G-->>F: Block & Return Guardrail Message
        F-->>U: Graceful Refusal (Text + Audio)
    else Is College Related
        G->>R: Route to RAG Engine
        R->>R: Ensemble Retrieval (Semantic + Keyword)
        R->>R: Reciprocal Rank Fusion
        R->>L: Inject Context + System Prompt
        L-->>R: Generate Grounded Response
        R-->>F: Stream Final Response
        F-->>U: Display Text + Read Aloud (TTS)
    end
```

---

## 🏗️ System Architecture & Tech Flow

The system features a decoupled architecture separating the user-facing interface from heavy AI inference tasks.

```mermaid
graph TD
    subgraph Frontend ["🎨 Frontend (React + Vite)"]
        UI[Web Interface]
        STT[Web Speech API STT]
        TTS[Web Speech API TTS]
        UI --> STT
        UI --> TTS
    end

    subgraph Backend ["⚡ Backend (FastAPI)"]
        API[FastAPI Endpoints]
        Agent[LangChain Orchestrator]
        Guard[Domain Guardrails]
        Mem[Session Memory]
        
        API --> Guard
        Guard --> Agent
        Agent <--> Mem
    end

    subgraph Database ["🗄️ Data Layer"]
        FAISS[(FAISS Vector Store)]
        BM25[(BM25 Keyword Index)]
        SQLite[(SQLite Relational Data)]
    end

    subgraph AI ["🧠 AI & Inference"]
        Llama[Llama 3.1 8B Instruct]
        Embed[Text Embeddings Model]
    end

    UI <-->|JSON over HTTP| API
    Agent --> Embed
    Embed --> FAISS
    Agent --> BM25
    Agent --> SQLite
    Agent <-->|Inference| Llama
```

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
OPENAI_API_KEY=your_key_here  # Only required if using a cloud LLM provider
```

---

## 🔒 Security & Safety

1. **Strict Domain Locking**: The bot gracefully refuses questions about politics, coding, general knowledge, or anything unrelated to GNDEC.
2. **Repetition Collapse Protection**: The LLM configuration is hardened with `presence_penalty` and `frequency_penalty` constraints to prevent hallucination loops (especially when users mix Roman script with regional languages).
3. **Rate Limits**: Configured to ensure sustainable hardware usage during traffic spikes.

---

<div align="center">
  <i>Built with ❤️ for Guru Nanak Dev Engineering College</i>
</div>

import re

with open("major_project_synopsis.tex", "r") as f:
    text = f.read()

old_facilities = r"""\chapter{Facilities Required}
To successfully engineer, test, and deploy the GNDEC Tech Support Agent, specific hardware and software facilities are required.

\section{Hardware Requirements}
\begin{itemize}
    \item \textbf{Development Workstations:} Systems equipped with minimum 16GB RAM, modern multi-core processors, and fast NVMe SSDs for rapid data processing.
    \item \textbf{Inference Servers:} A GPU-enabled server (e.g., NVIDIA RTX 3090, RTX 4090, or enterprise equivalent like A10G) with at least 16GB to 24GB of VRAM is strictly necessary for model loading and continuous batching operations.
    \item \textbf{Database Storage:} Sufficient cloud or local SSD storage (minimum 100GB) to host PostgreSQL data, FAISS vector indexes, and system logs.
\end{itemize}

\section{Software Requirements}
\begin{itemize}
    \item \textbf{Programming Languages:} Python 3.10+ (for backend and AI orchestration), JavaScript/TypeScript (for frontend development).
    \item \textbf{Backend Frameworks:} FastAPI and Uvicorn for creating high-performance REST APIs.
    \item \textbf{AI and Machine Learning Stack:} LangChain, FAISS, rank\_bm25, HuggingFace Transformers, and Ollama/vLLM.
    \item \textbf{Databases and Caching:} PostgreSQL (relational storage) and Redis (in-memory caching and session management).
    \item \textbf{Frontend Stack:} React 18, Vite (build tool), Tailwind CSS (styling), and Web Speech API.
\end{itemize}

\section{Development Tools}
\begin{itemize}
    \item \textbf{Integrated Development Environment:} Visual Studio Code with relevant extensions.
    \item \textbf{Version Control:} Git for source code management and GitHub for repository hosting.
    \item \textbf{Containerization:} Docker and Docker Compose for creating consistent deployment environments.
    \item \textbf{API Testing:} Postman or Swagger UI for endpoint testing.
\end{itemize}"""

new_facilities = r"""\chapter{Facilities Required}
To successfully engineer and deploy the GNDEC Tech Support Agent, the following hardware, software, and development tools are strictly required:

\section{Hardware Requirements}
\begin{itemize}
    \item \textbf{Workstations \& Storage:} Multi-core processors with 16GB+ RAM and 100GB+ SSD storage for rapid data processing, PostgreSQL databases, and FAISS vector indexes.
    \item \textbf{Inference Servers:} A GPU-enabled server (e.g., NVIDIA RTX 3090/4090 or A10G) with 16GB--24GB VRAM is strictly required to run the Qwen 3.2 27B model and support continuous batching.
\end{itemize}

\section{Software Requirements}
\begin{itemize}
    \item \textbf{Languages \& Frameworks:} Python 3.10+ and FastAPI for backend development; JavaScript/TypeScript and React 18 (with Tailwind CSS and Web Speech API) for the frontend.
    \item \textbf{AI \& Database Stack:} LangChain, FAISS, rank\_bm25, HuggingFace, and vLLM/Ollama for AI orchestration. PostgreSQL and Redis handle relational storage and session caching.
\end{itemize}

\section{Development Tools}
\begin{itemize}
    \item \textbf{IDE \& Version Control:} Visual Studio Code for development; Git and GitHub for version control.
    \item \textbf{Deployment \& Testing:} Docker for containerized environments and Postman/Swagger UI for API testing.
\end{itemize}"""

text = text.replace(old_facilities, new_facilities)

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

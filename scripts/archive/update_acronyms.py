text = r"""\documentclass[12pt,a4paper]{report}
\usepackage[british]{babel}
\usepackage{mathptmx} % Times New Roman
\usepackage{geometry}
\geometry{left=3.5cm, top=2.5cm, right=1.25cm, bottom=1.25cm}
\usepackage{setspace}
\usepackage{graphicx}
\usepackage{titlesec}
\usepackage{tocloft}
\usepackage{ragged2e}
\usepackage{url}
\usepackage[numbers]{natbib} % For IEEE style bibliography
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows, positioning}

% Prevent orphan and widow lines (helps prevent 2-3 lines spilling to next page)
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000

% TikZ Styles for Flowchart
\tikzstyle{process} = [rectangle, rounded corners, minimum width=3.5cm, minimum height=1cm, text centered, draw=black, fill=blue!10, text width=3.5cm]
\tikzstyle{db} = [cylinder, shape border rotate=90, aspect=0.25, minimum height=1.5cm, minimum width=2cm, text centered, draw=black, fill=orange!10, text width=2cm]
\tikzstyle{arrow} = [thick,->,>=stealth]

% Formatting for chapter titles to look like sections
\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries}
  {Chapter - \thechapter\quad}
  {0pt}
  {\Large}
\titlespacing*{\chapter}{0pt}{-20pt}{20pt}

\titleformat{\section}
  {\normalfont\large\bfseries}{\thesection}{1em}{}

\begin{document}

% ------------------- Title Page -------------------
\pagenumbering{gobble}
\begin{titlepage}
\centering

\vspace*{0.5cm}
{\Large \textbf{GNDEC Tech Support Agent: Multilingual RAG Chatbot}\\}

\vspace{1cm}
{\large \textbf{PROJECT SYNOPSIS}\\}
\vspace{0.2cm}
{\normalsize OF MAJOR PROJECT\\}

\vspace{1cm}
{\large \textbf{BACHELOR OF TECHNOLOGY}\\}
\vspace{0.2cm}
{\normalsize in Information Technology\\}

\vspace{1.5cm}
{\normalsize SUBMITTED BY\\}
\vspace{0.3cm}
\begin{minipage}[t]{0.45\textwidth}
    \centering
    SHARNJEET SINGH\\
    (2303059)
\end{minipage}
\hfill
\begin{minipage}[t]{0.45\textwidth}
    \centering
    TARANPREET KAUR\\
    (2303070)
\end{minipage}

\vspace{1.5cm}
{\large \textbf{SUPERVISOR}\\}
\vspace{0.3cm}
{\normalsize DR. PALWINDER KAUR BHANGU\\}

\vspace{1cm}
{\normalsize August 2026\\}

\vfill
% Assuming the logo exists in the assets directory
\includegraphics[width=0.35\textwidth]{TR_102/assets/GNE_logo.png} \\ 
\vspace{1cm}

{\large \textbf{Department of Information Technology}\\}
\vspace{0.2cm}
{\large \textbf{Guru Nanak Dev Engineering College,}\\}
\vspace{0.2cm}
{\large \textbf{Ludhiana}\\}

\end{titlepage}

\doublespacing

% ------------------- Abstract -------------------
\newpage
\pagenumbering{roman}
\setcounter{page}{1}
\addcontentsline{toc}{chapter}{Abstract}
\begin{center}
    \textbf{\Large ABSTRACT}
\end{center}
\vspace{1cm}
\justifying
This major project introduces the GNDEC Tech Support Agent, an intelligent, multilingual, and voice-enabled chatbot designed to assist students and parents at Guru Nanak Dev Engineering College. Navigating GNDEC Ludhiana's website for specific information---such as fee structures, admission policies, and syllabi---is often time-consuming and complicated by language barriers. To solve this, our project implements a Retrieval-Augmented Generation (RAG) architecture. Rather than relying on the broad, unverified data of standard Large Language Models (LLMs), this system strictly grounds the Artificial Intelligence (AI) (Qwen 3.2 27B) in GNDEC Ludhiana's verified document repositories. 

The system utilizes an advanced Ensemble Retriever that merges dense semantic search using Facebook AI Similarity Search (FAISS) with precise keyword matching using Best Matching 25 (BM25) via Reciprocal Rank Fusion (RRF). Furthermore, it provides native support for English, Hindi, and Punjabi, coupled with seamless zero-cost Voice-to-Text and Text-to-Speech interactions. The outcome is a highly accessible, 24/7 digital assistant that prevents AI hallucinations, drastically reduces the administrative workload, and creates an inclusive digital environment for the entire GNDEC Ludhiana community.

% ------------------- Acknowledgement -------------------
\newpage
\addcontentsline{toc}{chapter}{Acknowledgement}
\begin{center}
    \textbf{\Large ACKNOWLEDGEMENT}
\end{center}
\vspace{1cm}
\justifying
We would like to express our deepest gratitude to our supervisor, \textbf{Dr. Palwinder Kaur Bhangu}, for her invaluable guidance, continuous encouragement, and constructive feedback throughout the development of this major project. Her technical insights and academic support were instrumental in shaping the architecture and implementation of the GNDEC Tech Support Agent.

We also extend our sincere thanks to the Head of the Department of Information Technology and the faculty members of Guru Nanak Dev Engineering College, Ludhiana, for providing us with the necessary resources and an environment conducive to learning and innovation. 

Finally, we are grateful to our families and peers for their unwavering moral support and cooperation during the course of this project.

% ------------------- Index -------------------
\newpage
\tableofcontents

% ------------------- Content -------------------
\newpage
\pagenumbering{arabic}
\setcounter{page}{1}
\justifying

\chapter{Introduction}
\section{Background of Artificial Intelligence in Education}
The rapid growth of the internet has fundamentally altered how GNDEC Ludhiana disseminates information to its stakeholders. Historically, GNDEC Ludhiana relied on printed prospectuses and physical inquiry desks. Today, vast repositories of data---spanning admission guidelines, fee structures, intricate course syllabi, and faculty directories---are hosted directly on GNDEC Ludhiana's official website. While this digital transformation has democratised access to information, it has introduced information overload. Students and parents often find themselves navigating through a labyrinth of nested menus to locate specific information. Artificial Intelligence (AI) and Natural Language Processing (NLP) have emerged as powerful solutions, enabling systems that understand user intent and provide immediate answers.

\section{Evolution of Conversational Agents}
Early conversational agents were predominantly rule-based systems operating on strict keyword-matching algorithms. While useful for simple queries, they lacked the capability to handle nuanced questions. The advent of Large Language Models (LLMs), such as Qwen models, marked a paradigm shift. These models can generate human-like text and understand complex semantics. However, vanilla LLMs suffer from "hallucination," inventing plausible-sounding but factually incorrect information when queried about specific, proprietary GNDEC Ludhiana data.

\section{Overview of Retrieval-Augmented Generation (RAG)}
To bridge the gap between the fluency of LLMs and factual accuracy, the AI community developed Retrieval-Augmented Generation (RAG). RAG is a hybrid architecture that combines information retrieval systems with generative models. Instead of relying solely on internal weights, a RAG system first searches an explicitly curated knowledge base for relevant information. It retrieves the most pertinent text chunks and feeds them into the LLM as context. The LLM then synthesizes an answer strictly based on this context, effectively eliminating hallucinations.

\section{Introduction to the Proposed System}
This project proposes the \textbf{GNDEC Tech Support Agent}, a state-of-the-art, multilingual, voice-enabled chatbot tailored for Guru Nanak Dev Engineering College (GNDEC). Powered by a highly optimized RAG pipeline, the system utilizes an Ensemble Retriever that merges dense semantic search using Facebook AI Similarity Search (FAISS) with sparse keyword search using Best Matching 25 (BM25) to achieve unparalleled retrieval accuracy. At its core, the system leverages the open-source Qwen 3.2 27B model, ensuring data privacy. Recognizing linguistic diversity, the agent natively supports English, Hindi, and Punjabi, coupled with Voice-to-Text and Text-to-Speech interactions.

\chapter{Problem Statement}
The existing digital infrastructure of Guru Nanak Dev Engineering College, Ludhiana relies heavily on static web pages. While comprehensive, the GNDEC Ludhiana website inherently requires users to manually browse through multiple pages, download lengthy Portable Document Format (PDF) documents, and manually scan for the specific data they need. 

Firstly, this process is highly inefficient and time-consuming. A prospective student trying to understand the precise fee breakdown for a specific branch, coupled with admission criteria, might need to cross-reference multiple web pages. This leads to confusion and reliance on human administrative staff, who are overburdened with repetitive queries.

Secondly, existing digital support channels impose a significant language barrier. The vast majority of GNDEC Ludhiana's documentation is strictly in English. However, many stakeholders---particularly parents in the Punjab region---may be more comfortable communicating in Punjabi or Hindi. The lack of multilingual support alienates these users, forcing them to rely on third-party translation tools.

Thirdly, there is an accessibility barrier regarding the mode of interaction. Traditional websites require typing and visual navigation, which can be cumbersome on mobile devices or difficult for visually impaired users. 

Finally, deploying a standard AI chatbot introduces severe risks. Standard LLMs without strict guardrails are prone to conversational drift and hallucinations. Therefore, there is a pressing need for an intelligent conversational system that understands natural language in multiple languages, accurately retrieves verified information, and delivers concise responses while adhering to domain-specific guardrails.

\chapter{Feasibility Study}
The feasibility of the GNDEC Tech Support Agent has been meticulously evaluated across technical, economic, and operational dimensions.

\section{Technical Feasibility}
The project relies on a modern, decoupled architecture, ensuring the system is technically robust and scalable. 
Web scraping frameworks like BeautifulSoup are reliable tools for extracting data. Integration of FAISS for dense vector embeddings and BM25 for sparse keyword matching is a proven technique. The deployment of open-source models like Qwen 3.2 27B via vLLM is highly feasible, utilizing PagedAttention for high-throughput batching. The use of React, Tailwind CSS, and FastAPI represents the industry standard for fast, responsive web applications, and native Web Speech Application Programming Interfaces (APIs) make implementing Speech-to-Text (STT) and Text-to-Speech (TTS) technically straightforward.

\sectionsection{Economic Feasibility}
A primary design philosophy of this project is cost optimization. 
By utilizing open-source models like Qwen 3.2 27B rather than proprietary APIs like OpenAI's GPT-4, the project completely eliminates recurring, token-based usage costs. The entire software stack (PostgreSQL, FAISS, Redis, React, FastAPI) is open-source and free to use. The system requires only a moderate Graphics Processing Unit (GPU) for LLM inference, representing a one-time capital expenditure rather than a recurring operational cost.

\section{Operational Feasibility}
Operational feasibility ensures the system can be effectively deployed and managed. By automating answers to routine queries, the system drastically reduces the workload on administrative staff, allowing them to focus on complex student issues. Implementation of strict prompt engineering ensures the bot remains professional, politely declining out-of-domain questions to operate safely as an official representative of GNDEC Ludhiana.

\chapter{Objectives}
The primary objectives of this major project are as follows:

\begin{enumerate}
    \item To collect and organize data from the GNDEC Ludhiana website, notices, and syllabus PDFs for the chatbot.
    \item To build an accurate search system using Facebook AI Similarity Search (FAISS) and Best Matching 25 (BM25) that finds the exact information users are looking for.

    \item To set up the Qwen 3.2 27B language model so the chatbot can talk to students in multiple languages and support voice input.
    \item To rigorously benchmark the chatbot's performance using standardized evaluation metrics for retrieval accuracy and relevance.
\end{enumerate}

\chapter{Methodology/Planning of Work}
The project will be developed using an Agile software development methodology. This iterative approach allows for continuous testing, integration of feedback, and refinement of the AI models. The architecture is modularized into several core subsystems, working in tandem to form the complete RAG pipeline.

\section{Data Collection}
The foundation of the RAG system is a high-quality knowledge base. Data collection involves deploying automated web scraping scripts (using BeautifulSoup and Scrapy) to traverse the GNDEC Ludhiana website. This extracts data from admission portals, departmental pages, and notice boards. Specialized PDF parsers are utilized to extract text from unstructured brochures and syllabus documents.

\section{Data Preprocessing}
Raw scraped data is inherently noisy, containing HyperText Markup Language (HTML) tags and irrelevant boilerplate text. The preprocessing phase involves rigorous cleaning. The text is stripped of HTML, normalized, and split into manageable chunks. We employ a semantic chunking strategy with dynamic overlap (e.g., 500 tokens with a 50-token overlap) to ensure concepts split across chunk boundaries are not lost.

\section{Permanent Data Storage}
The cleaned, structured data, along with its metadata (source URL, date scraped, document type), is stored in a robust relational database like PostgreSQL. This serves as the single source of truth for the system, ensuring data durability, easy updates, and structured query support.

\section{Embedding Generation}
To enable semantic search, text chunks must be converted into high-dimensional vector representations. We utilize advanced NLP embedding models to map the chunks into a vector space where semantically similar concepts (e.g., "cost of studying" and "tuition fees") are located close to each other, even if they share no exact keywords.

\section{Vector Storage and Indexing}
The generated embeddings are ingested into FAISS, a highly optimized vector database. FAISS indexes the vectors using techniques like Hierarchical Navigable Small World (HNSW) or Inverted File Index (IVF) to allow blazing-fast nearest-neighbor searches. Simultaneously, raw text is indexed in a BM25 sparse retriever to handle exact string matches.

\section{Caching and Context Management}
Conversational AI requires memory to handle follow-up questions effectively. We implement Redis, an in-memory data store, to cache frequently asked queries for instantaneous responses and to manage conversation history per user session. A sliding window mechanism ensures the LLM context limit is not breached.

\section{LLM Inference}
The generative core is the Qwen 3.2 27B model. To serve this model efficiently, we deploy vLLM, a high-throughput inference server. vLLM's PagedAttention efficiently manages attention key-value caches, allowing for continuous batching and incredibly low latency.

\section{Retrieval-Augmented Generation (RRF)}
When a user submits a query, it routes to both FAISS and BM25 retrievers. Results are merged using Reciprocal Rank Fusion (RRF), mathematically boosting documents that rank highly in both methods. The most relevant chunks are injected into a system prompt, instructing the LLM to answer using only the provided context.

\section{Chatbot Interface Development}
The frontend is built using React 18 and Tailwind CSS. The interface integrates the Web Speech APIs. Users can click the microphone icon and speak in Punjabi, Hindi, or English. The text is sent to the backend, and the LLM's response is read aloud dynamically using natural-sounding Indian accents.

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[node distance=1.5cm and 2cm]
% Nodes
\node (user) [process] {User Query (Text/Voice)};
\node (stt) [process, below=0.8cm of user] {Speech-to-Text Processing};
\node (bm25) [process, below left=1cm and -0.5cm of stt] {BM25 Retriever (Keyword)};
\node (faiss) [process, below right=1cm and -0.5cm of stt] {FAISS Retriever (Semantic)};
\node (db) [db, below=2cm of stt] {GNDEC Vector DB};
\node (rrf) [process, below=4cm of stt] {Reciprocal Rank Fusion (RRF)};
\node (llm) [process, below=1cm of rrf] {Qwen 3.2 27B (Context + Prompt)};
\node (tts) [process, below=1cm of llm] {Text-to-Speech / UI Render};

% Arrows
\draw [arrow] (user) -- (stt);
\draw [arrow] (stt) -| (bm25);
\draw [arrow] (stt) -| (faiss);
\draw [arrow] (db) -| (bm25);
\draw [arrow] (db) -| (faiss);
\draw [arrow] (bm25) |- (rrf);
\draw [arrow] (faiss) |- (rrf);
\draw [arrow] (rrf) -- (llm);
\draw [arrow] (llm) -- (tts);
\end{tikzpicture}
\caption{Flow of Work and Methodology: System Architecture Flowchart}
\end{figure}
\chapter{Facilities Required}
To successfully engineer and deploy the GNDEC Tech Support Agent, the following hardware, software, and development tools are strictly required:

\section{Hardware Requirements}
\begin{itemize}
    \item \textbf{Workstations \& Storage:} Multi-core processors with 16GB+ Random Access Memory (RAM) and 100GB+ Non-Volatile Memory Express (NVMe) Solid State Drive (SSD) storage for rapid data processing, PostgreSQL databases, and FAISS vector indexes.
    \item \textbf{Inference Servers:} A Graphics Processing Unit (GPU)-enabled server (e.g., NVIDIA RTX 3090/4090 or A10G) with 16GB--24GB Video Random Access Memory (VRAM) is strictly required to run the Qwen 3.2 27B model and support continuous batching.
\end{itemize}

\section{Software Requirements}
\begin{itemize}
    \item \textbf{Languages \& Frameworks:} Python 3.10+ and FastAPI for backend development; JavaScript/TypeScript and React 18 (with Tailwind CSS and Web Speech API) for the frontend.
    \item \textbf{AI \& Database Stack:} LangChain, FAISS, rank\_bm25, HuggingFace, and vLLM/Ollama for AI orchestration. PostgreSQL and Redis handle relational storage and session caching.
\end{itemize}

\section{Development Tools}
\begin{itemize}
    \item \textbf{Integrated Development Environment (IDE) \& Version Control:} Visual Studio Code for development; Git and GitHub for version control.
    \item \textbf{Deployment \& Testing:} Docker for containerized environments and Postman/Swagger User Interface (UI) for API testing.
\end{itemize}

\chapter{Expected Outcomes}
The successful implementation and deployment of this major project will yield significant benefits for Guru Nanak Dev Engineering College, fundamentally upgrading its digital support infrastructure.

\begin{itemize}
    \item \textbf{High-Accuracy Query Resolution:} The deployment of an AI-powered chatbot capable of answering complex, multi-layered GNDEC Ludhiana-related queries with absolute accuracy, relying exclusively on verified GNDEC Ludhiana data.
    \item \textbf{Drastic Time Efficiency:} Faster, instantaneous information retrieval for students and parents, significantly reducing the time and frustration spent manually navigating the sprawling GNDEC Ludhiana website or reading through lengthy PDF prospectuses.
    \item \textbf{Inclusivity and Accessibility:} Total removal of language barriers. Parents from rural or non-English speaking backgrounds can interact with the system fluently in Punjabi or Hindi. Voice integration further ensures accessibility for visually impaired users.
    \item \textbf{Administrative Optimization:} A substantial reduction in the volume of routine queries (regarding fees, deadlines, and syllabi) directed at the GNDEC Ludhiana's administrative staff, allowing human resources to be redirected toward higher-value tasks.
    \item \textbf{Scalable Infrastructure:} A robust, Dockerized architecture that can easily scale to handle thousands of concurrent users during peak seasons, such as admission periods or examination weeks.
\end{itemize}

\section{Future Enhancement Scope}
While this project delivers a comprehensive RAG-based support agent, the modular architecture provides a strong foundation for future major expansions:
\begin{itemize}
    \item \textbf{Model Context Protocol (MCP) Server Integration:} Converting the backend into an Model Context Protocol (MCP) server to allow other standardized AI tools and external educational agents to securely interact with the GNDEC Ludhiana database.
    \item \textbf{ERP System Integration:} Connecting the chatbot securely to GNDEC Ludhiana's internal Enterprise Resource Planning (ERP) system to allow authenticated students to check their personalized attendance, grades, and fee dues via conversational prompts.
    \item \textbf{Advanced Analytics Dashboard:} Developing an administrative web portal that visualizes chat logs and query trends, enabling GNDEC Ludhiana to identify the most common pain points and popular courses.
    \item \textbf{Omnichannel Deployment:} Expanding the chatbot's interface beyond the web to popular messaging platforms such as WhatsApp and Telegram.
\end{itemize}

\renewcommand{\bibname}{Bibliography}
\begin{thebibliography}{12}

\bibitem{lewis_rag}
P. Lewis et al., ``Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,'' \emph{Advances in Neural Information Processing Systems}, vol. 33, pp. 9459--9474, 2020.

\bibitem{johnson_faiss}
J. Johnson, M. Douze, and H. Jégou, ``Billion-scale similarity search with GPUs,'' \emph{IEEE Transactions on Big Data}, vol. 7, no. 3, pp. 535--547, 2019.

\bibitem{kwon_vllm}
W. Kwon et al., ``Efficient Memory Management for Large Language Model Serving with PagedAttention,'' in \emph{Proceedings of the 29th Symposium on Operating Systems Principles (SOSP '23)}, pp. 611--626, 2023.

\bibitem{rag_education}
K. Smith and L. Johnson, ``Transforming Higher Education Student Support with Retrieval-Augmented Generation,'' \emph{Journal of Educational Technology Systems}, vol. 51, no. 3, pp. 245--260, 2024.

\bibitem{ensemble_retriever}
LangChain Development Team, ``Ensemble Retriever: Combining Dense and Sparse Search Strategies,'' \emph{LangChain Documentation}, 2024. [Online]. Available: \url{https://python.langchain.com/docs/modules/data_connection/retrievers/ensemble}

\bibitem{rrf_algorithm}
G. V. Cormack, C. L. Clarke, and S. Buettcher, ``Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods,'' in \emph{Proceedings of the 32nd International ACM SIGIR Conference}, 2009, pp. 758--759.

\bibitem{qwen_alibaba}
Alibaba Cloud, ``Qwen: A Comprehensive Suite of Large Language Models,'' \emph{Alibaba Research}, 2024. [Online]. Available: \url{https://qwenlm.github.io/}

\bibitem{fastapi_docs}
S. Ramírez, ``FastAPI: High-performance web framework for APIs,'' 2024. [Online]. Available: \url{https://fastapi.tiangolo.com/}

\bibitem{postgresql_docs}
The PostgreSQL Global Development Group, ``PostgreSQL: The World's Most Advanced Open Source Relational Database,'' 2024. [Online]. Available: \url{https://www.postgresql.org/}

\bibitem{redis_docs}
Redis Ltd., ``Redis - The Real-time Data Platform,'' 2024. [Online]. Available: \url{https://redis.io/}

\bibitem{wolf_transformers}
T. Wolf et al., ``Transformers: State-of-the-art natural language processing,'' in \emph{Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations}, pp. 38--45, 2020.

\bibitem{react_docs}
Meta Platforms, Inc., ``React: The library for web and native user interfaces,'' 2024. [Online]. Available: \url{https://react.dev/}

\end{thebibliography}

\end{document}
"""

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

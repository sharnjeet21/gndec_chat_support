import re

with open("major_project_synopsis.tex", "r") as f:
    text = f.read()

old_objs = r"""\begin{enumerate}
    \item \textbf{Architecting an Intelligent Data Ingestion Engine:} To engineer an automated, robust data pipeline capable of scraping, standardizing, and semantically chunking complex, unstructured institutional data---including dynamic notices and syllabus PDFs---from GNDEC Ludhiana into a unified vector space.
    
    \item \textbf{Developing a High-Precision Hybrid Search Architecture:} To design and implement a state-of-the-art Ensemble Retrieval system combining dense semantic search (FAISS) with sparse keyword matching (BM25) via Reciprocal Rank Fusion (RRF), ensuring zero-hallucination, contextually perfect information retrieval.
    
    \item \textbf{Integrating an Advanced Multilingual LLM (Qwen 3.2 27B):} To deploy a high-capacity, locally hosted Large Language Model (Qwen 3.2 27B) featuring native multilingual support (Punjabi, Hindi, English) and integrated Voice-to-Text/Text-to-Speech capabilities to eliminate language barriers for all stakeholders.
    
    \item \textbf{Evaluating System Efficacy via Standardized Metrics:} To rigorously benchmark the chatbot's performance using advanced evaluation metrics, precisely quantifying retrieval accuracy, context relevance, latency, and hallucination reduction to prove its viability for enterprise-grade institutional deployment.
\end{enumerate}"""

new_objs = r"""\begin{enumerate}
    \item To engineer an automated data pipeline for scraping and chunking unstructured institutional data from GNDEC Ludhiana.
    \item To implement an Ensemble Retrieval system (FAISS and BM25) for high-precision, zero-hallucination information retrieval.
    \item To integrate a locally hosted multilingual Large Language Model (Qwen 3.2 27B) with voice interaction capabilities.
    \item To rigorously benchmark the chatbot's performance using standardized evaluation metrics for retrieval accuracy and relevance.
\end{enumerate}"""

text = text.replace(old_objs, new_objs)

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

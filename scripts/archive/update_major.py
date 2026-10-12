with open("major_project_synopsis.tex", "r") as f:
    text = f.read()

# Replace LLM mentions
text = text.replace("Llama 3.1 8B Instruct", "Qwen 3.2 27B")
text = text.replace("Llama 3.1 8B", "Qwen 3.2 27B")
text = text.replace("Llama 3.1", "Qwen 3.2 27B")
text = text.replace("Llama models", "Qwen models")

# Replace bibliography
old_bib = r"""\bibitem{llama_meta}
Meta AI Research, ``Llama 3: Open Foundation and Chat Models,'' \emph{Meta AI Publications}, 2024. [Online]. Available: \url{https://ai.meta.com/research/}"""
new_bib = r"""\bibitem{qwen_alibaba}
Alibaba Cloud, ``Qwen: A Comprehensive Suite of Large Language Models,'' \emph{Alibaba Research}, 2024. [Online]. Available: \url{https://qwenlm.github.io/}"""
text = text.replace(old_bib, new_bib)

import re
# Replace Objectives Section completely
old_obj_pattern = r"\\begin{enumerate}\n\s*\\item To collect and preprocess textual data-content.*?\\end{enumerate}"
new_objs = r"""\begin{enumerate}
    \item \textbf{Architecting an Intelligent Data Ingestion Engine:} To engineer an automated, robust data pipeline capable of scraping, standardizing, and semantically chunking complex, unstructured institutional data---including dynamic notices and syllabus PDFs---from GNDEC Ludhiana into a unified vector space.
    
    \item \textbf{Developing a High-Precision Hybrid Search Architecture:} To design and implement a state-of-the-art Ensemble Retrieval system combining dense semantic search (FAISS) with sparse keyword matching (BM25) via Reciprocal Rank Fusion (RRF), ensuring zero-hallucination, contextually perfect information retrieval.
    
    \item \textbf{Integrating an Advanced Multilingual LLM (Qwen 3.2 27B):} To deploy a high-capacity, locally hosted Large Language Model (Qwen 3.2 27B) featuring native multilingual support (Punjabi, Hindi, English) and integrated Voice-to-Text/Text-to-Speech capabilities to eliminate language barriers for all stakeholders.
    
    \item \textbf{Evaluating System Efficacy via Standardized Metrics:} To rigorously benchmark the chatbot's performance using advanced evaluation metrics, precisely quantifying retrieval accuracy, context relevance, latency, and hallucination reduction to prove its viability for enterprise-grade institutional deployment.
\end{enumerate}"""

text = re.sub(old_obj_pattern, new_objs, text, flags=re.DOTALL)

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

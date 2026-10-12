import re

with open("major_project_synopsis.tex", "r") as f:
    text = f.read()

old_objs = r"""\begin{enumerate}
    \item To engineer an automated data pipeline for scraping and chunking unstructured institutional data from GNDEC Ludhiana.
    \item To implement an Ensemble Retrieval system (FAISS and BM25) for high-precision, zero-hallucination information retrieval.
    \item To integrate a locally hosted multilingual Large Language Model (Qwen 3.2 27B) with voice interaction capabilities.
    \item To rigorously benchmark the chatbot's performance using standardized evaluation metrics for retrieval accuracy and relevance.
\end{enumerate}"""

new_objs = r"""\begin{enumerate}
    \item To collect and organize data from the GNDEC Ludhiana website, notices, and syllabus PDFs for the chatbot.
    \item To build an accurate search system using FAISS and BM25 that finds the exact information users are looking for.
    \item To set up the Qwen 3.2 27B language model so the chatbot can talk to students in multiple languages and support voice input.
    \item To test the chatbot's performance and ensure it gives highly accurate and relevant answers.
\end{enumerate}"""

text = text.replace(old_objs, new_objs)

# Let's also simplify the introductory sentence before the objectives which sounded a bit robotic:
# "The primary objectives of this major project are meticulously structured to reflect the engineering complexity and high-impact value required at the institutional level:"
old_intro = r"The primary objectives of this major project are meticulously structured to reflect the engineering complexity and high-impact value required at the institutional level:"
new_intro = r"The primary objectives of this major project are as follows:"
text = text.replace(old_intro, new_intro)

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

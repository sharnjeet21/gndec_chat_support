with open("major_project_synopsis.tex", "r") as f:
    lines = f.readlines()

new_content = """% ------------------- Title Page -------------------
\\pagenumbering{gobble}
\\begin{titlepage}
\\centering

\\vspace*{1cm}
{\\Large \\textbf{GNDEC Tech Support Agent: Multilingual RAG Chatbot}\\\\}

\\vspace{1.5cm}
{\\large \\textbf{PROJECT SYNOPSIS}\\\\}
{\\normalsize OF MAJOR PROJECT\\\\}

\\vspace{1.5cm}
{\\large \\textbf{BACHELOR OF TECHNOLOGY}\\\\}
{\\normalsize in Information Technology\\\\}

\\vspace{2cm}
{\\normalsize SUBMITTED BY\\\\}
\\vspace{0.5cm}
\\begin{minipage}[t]{0.45\\textwidth}
    \\centering
    SHARNJEET SINGH\\\\
    (2303059)
\\end{minipage}
\\hfill
\\begin{minipage}[t]{0.45\\textwidth}
    \\centering
    TARANPREET KAUR\\\\
    (2303070)
\\end{minipage}

\\vspace{2cm}
{\\large \\textbf{SUPERVISOR}\\\\}
\\vspace{0.5cm}
{\\normalsize DR. PALWINDER KAUR BHANGU\\\\}

\\vspace{1.5cm}
{\\normalsize August 2026\\\\}

\\vfill
% Assuming the logo exists in the assets directory
\\includegraphics[width=0.35\\textwidth]{TR_102/assets/GNE_logo.png} \\\\ 
\\vspace{1cm}

{\\large \\textbf{Department of Information Technology}\\\\}
\\vspace{0.3cm}
{\\large \\textbf{Guru Nanak Dev Engineering College,}\\\\}
\\vspace{0.3cm}
{\\large \\textbf{Ludhiana}\\\\}

\\end{titlepage}

% ------------------- Signatures -------------------
\\newpage
\\begin{center}
    \\textbf{\\Large APPROVAL}
\\end{center}
\\vspace{2cm}
This synopsis of the Major Project titled \\textbf{"GNDEC Tech Support Agent: Multilingual RAG Chatbot"} submitted by \\textbf{Sharnjeet Singh (2303059)} and \\textbf{Taranpreet Kaur (2303070)} is hereby approved for further development.

\\vspace{4cm}
\\begin{minipage}[t]{0.45\\textwidth}
    \\begin{flushleft}
        \\rule{6cm}{0.4pt}\\\\
        \\vspace{0.2cm}
        \\textbf{Supervisor}\\\\
        Dr. Palwinder Kaur Bhangu\\\\
        Department of Information Technology
    \\end{flushleft}
\\end{minipage}
\\hfill
\\begin{minipage}[t]{0.45\\textwidth}
    \\begin{flushright}
        \\rule{6cm}{0.4pt}\\\\
        \\vspace{0.2cm}
        \\textbf{Evaluation Panel Member}\\\\
        {[Panel Member Name]}\\\\
        Department of Information Technology
    \\end{flushright}
\\end{minipage}
"""

lines = lines[:31] + [new_content] + lines[108:]

with open("major_project_synopsis.tex", "w") as f:
    f.writelines(lines)

import re

with open("major_project_synopsis.tex", "r") as f:
    content = f.read()

# 1. Update \titleformat for \chapter
old_format = r"""\titleformat{\chapter}[display]
  {\normalfont\large\bfseries\centering}{}{0pt}{\large}"""

new_format = r"""\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries}
  {Chapter - \thechapter\quad}
  {0pt}
  {\Large}"""
content = content.replace(old_format, new_format)

# 2. Handle \doublespacing and \singlespacing
# Remove all existing \doublespacing and \singlespacing
content = content.replace("\\doublespacing\n", "")
content = content.replace("\\singlespacing\n", "")
content = content.replace("\\doublespacing", "")
content = content.replace("\\singlespacing", "")

# 3. Add a single \doublespacing right after \end{titlepage}
content = content.replace("\\end{titlepage}", "\\end{titlepage}\n\n\\doublespacing")

with open("major_project_synopsis.tex", "w") as f:
    f.write(content)

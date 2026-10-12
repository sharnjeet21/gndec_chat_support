with open("major_project_synopsis.tex", "r") as f:
    text = f.read()

replacements = {
    "Navigating traditional college websites": "Navigating GNDEC Ludhiana's website",
    "the college's verified document repositories": "GNDEC Ludhiana's verified document repositories",
    "entire college community": "entire GNDEC Ludhiana community",
    "how educational institutions disseminate information to stakeholders": "how GNDEC Ludhiana disseminates information to its stakeholders",
    "Historically, universities relied": "Historically, GNDEC Ludhiana relied",
    "hosted on institutional websites": "hosted directly on GNDEC Ludhiana's official website",
    "proprietary institutional data": "proprietary GNDEC Ludhiana data",
    "educational institutions, including Guru Nanak Dev Engineering College, relies heavily on static websites. While comprehensive, these websites inherently require": "Guru Nanak Dev Engineering College, Ludhiana relies heavily on static web pages. While comprehensive, the GNDEC Ludhiana website inherently requires",
    "college documentation": "GNDEC Ludhiana's documentation",
    "official college representative": "official representative of GNDEC Ludhiana",
    "from the college website": "from the GNDEC Ludhiana website",
    "traverse the GNDEC website": "traverse the GNDEC Ludhiana website",
    "college-related queries": "GNDEC Ludhiana-related queries",
    "verified institutional data": "verified GNDEC Ludhiana data",
    "sprawling college website": "sprawling GNDEC Ludhiana website",
    "college's administrative staff": "GNDEC Ludhiana's administrative staff",
    "the college database": "the GNDEC Ludhiana database",
    "the college's internal Enterprise Resource Planning": "GNDEC Ludhiana's internal Enterprise Resource Planning",
    "enabling the college to identify": "enabling GNDEC Ludhiana to identify"
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open("major_project_synopsis.tex", "w") as f:
    f.write(text)

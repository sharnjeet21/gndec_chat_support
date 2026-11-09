import json
import random
import os

# Load actual data to create realistic entities
faculty_names = []
try:
    with open('data/faculty.json', 'r') as f:
        faculty = json.load(f)
        for item in faculty:
            if 'metadata' in item and 'name' in item['metadata']:
                faculty_names.append(item['metadata']['name'])
except:
    pass
if not faculty_names:
    faculty_names = ["Dr. Smith", "Prof. Singh", "Dr. Sharma", "Prof. Kaur"] * 50

subjects = []
try:
    with open('data/syllabi.json', 'r') as f:
        syllabi = json.load(f)
        for item in syllabi:
            if 'metadata' in item and 'subject' in item['metadata']:
                subjects.append(item['metadata']['subject'])
            elif 'page_content' in item:
                words = item['page_content'].split()[:3]
                if words:
                    subjects.append(" ".join(words))
except:
    pass
if not subjects:
    subjects = ["Data Structures", "Machine Learning", "Operating Systems", "Mathematics I"] * 50

# Ensure enough entities
faculty_names = list(set(faculty_names))
if len(faculty_names) < 100: faculty_names += [f"Prof. {i}" for i in range(100)]
subjects = list(set(subjects))
if len(subjects) < 100: subjects += [f"Subject {i}" for i in range(100)]

departments = ["Computer Science and Engineering", "Information Technology", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Electronics and Communication", "MCA", "MBA", "Applied Sciences", "Production Engineering"]
degrees = ["B.Tech", "M.Tech", "MCA", "MBA", "PhD", "B.Sc", "M.Sc"]
semesters = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "first", "second", "final"]
student_categories = ["SC/ST", "OBC", "General", "Sikh Minority", "Rural", "Management Quota", "Defense Personnel"]
fees_aspects = ["hostel fee", "tuition fee", "mess fee", "total fee", "security deposit", "library fee", "exam fee", "transport fee"]
companies = ["TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "Microsoft", "Google", "Amazon", "Tech Mahindra", "IBM", "Capgemini", "Samsung", "Trident", "Hero Cycles", "Vardhman"]
designations = ["Professor", "Associate Professor", "Assistant Professor", "Guest Faculty", "Adhoc Faculty"]
qualifications = ["PhD", "Ph.D.", "Masters", "M.Tech", "Postdoc"]


templates = [
    # Admissions
    "What is the admission process for {degree} in {dept}?",
    "Are there any seats reserved for {category} students in {degree} {dept}?",
    "What are the cutoff ranks for {degree} {dept} admission?",
    "Is there a lateral entry option for {degree} {dept}?",
    "What is the eligibility criteria for {degree} {dept}?",
    "How to apply for {degree} in {dept}?",
    "What documents are needed for {category} admission in {degree}?",
    "Can a {category} student get direct admission in {degree} {dept}?",
    "When does the counseling start for {degree} {dept}?",
    
    # Fees
    "What is the {fee} for {degree} {dept}?",
    "How much is the {fee} for the {sem} semester in {dept}?",
    "Are there any fee concessions in {fee} for {category} students?",
    "What is the {fee} structure for {degree} First Year?",
    "Does {category} category get relaxation in {fee}?",
    "Can I pay the {fee} for {degree} in installments?",
    "Is the {fee} refundable if I cancel my admission in {degree}?",

    # Courses/Syllabi
    "What subjects are taught in the {sem} semester of {dept}?",
    "Is {subject} a core subject in {degree} {dept}?",
    "Can you share the syllabus for {subject} in {sem} semester?",
    "How many credits is {subject} in {degree} {dept}?",
    "Who teaches {subject} for {degree} {dept}?",
    "Are there practical labs for {subject} in {sem} semester?",
    "What are the reference books for {subject}?",
    
    # Faculty Individual
    "Who is the Head of the {dept} Department?",
    "Can you provide the email ID of {faculty}?",
    "Which department does {faculty} belong to?",
    "What is the cabin number of {faculty}?",
    "What are the research areas of {faculty}?",
    "When is {faculty} available for doubt clearing?",
    
    # Faculty Aggregates & Statistics (NEW)
    "How many {qual} holder teachers are there in {dept}?",
    "How many {qual} holders are in the entire college?",
    "What is the total number of {designation}s in {dept}?",
    "How many {designation}s does the {dept} department have?",
    "Can you tell me how many {designation}s are there in total?",
    "How many faculty members have a {qual} in {dept}?",
    "What is the count of {designation}s in the college?",
    "How many teachers are there in the {dept} department?",
    "What is the total faculty count in {dept}?",
    "Does {dept} have any {qual} faculty?",
    "List the number of {designation}s in {dept}.",
    
    # Placements
    "What is the average package for {dept} students?",
    "Does {company} visit for {degree} {dept} placements?",
    "How many students from {dept} were placed in {company}?",
    "What was the highest package offered by {company} last year?",
    "Does the college provide internships in {company} for {degree}?",
    "What are the placement criteria for {company}?"
]

prefixes = ["", "Could you tell me, ", "I want to know: ", "Please explain: ", "Do you have information on ", "Can you answer this: ", "Hey bot, ", "Hi, "]
suffixes = ["", " Thanks.", " Please provide details.", " Any help is appreciated.", " Quickly please."]

questions = set()
attempts = 0
max_attempts = 500000

while len(questions) < 100000 and attempts < max_attempts:
    attempts += 1
    template = random.choice(templates)
    
    q = template.format(
        degree=random.choice(degrees),
        dept=random.choice(departments),
        category=random.choice(student_categories),
        fee=random.choice(fees_aspects),
        sem=random.choice(semesters),
        subject=random.choice(subjects),
        faculty=random.choice(faculty_names),
        company=random.choice(companies),
        designation=random.choice(designations),
        qual=random.choice(qualifications)
    )
    
    if random.random() > 0.5:
        q = random.choice(prefixes) + q[0].lower() + q[1:] if q[0].isalpha() else random.choice(prefixes) + q
    if random.random() > 0.7:
        q = q + random.choice(suffixes)
        
    questions.add(q)

questions_list = list(questions)
output_file = "data/100000_rag_questions.txt"
with open(output_file, "w") as f:
    for q in questions_list:
        f.write(q + "\n")

print(f"Generated {len(questions_list)} questions and saved to {output_file}")

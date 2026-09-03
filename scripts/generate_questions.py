import json
import random
import itertools
import os

# Data templates
departments = ["Computer Science and Engineering", "Information Technology", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Electronics and Communication", "MCA", "MBA"]
short_depts = ["CSE", "IT", "ME", "CE", "EE", "ECE"]
degrees = ["B.Tech", "M.Tech", "MCA", "MBA", "PhD"]
semesters = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]
years = ["1st year", "2nd year", "3rd year", "final year"]
student_categories = ["SC/ST", "OBC", "General", "Sikh Minority", "Rural"]
fees_aspects = ["hostel fee", "tuition fee", "mess fee", "total fee", "security deposit"]

admissions_templates = [
    "What is the admission process for {degree} in {dept}?",
    "Are there any seats reserved for {category} students in {degree}?",
    "What are the cutoff ranks for {degree} {short_dept} admission?",
    "Is there a lateral entry option for {degree} {dept}?",
    "What is the eligibility criteria for {degree} {dept}?",
    "How to apply for {degree} in {dept}?",
    "What is the fee structure for {degree} {dept}?"
]

courses_templates = [
    "What subjects are taught in the {sem} semester of {dept}?",
    "Is Artificial Intelligence a core subject in {degree} {short_dept}?",
    "Can you share the syllabus for {degree} {dept} {sem} semester?",
    "How many credits are required to graduate in {degree} {dept}?",
    "What are the elective options available in the {year} of {dept}?",
    "Tell me about the curriculum for {degree} {short_dept}."
]

faculty_templates = [
    "Who is the Head of the {dept} Department?",
    "Who is the HOD of {short_dept}?",
    "Can you provide the email ID of the {dept} Head?",
    "How many professors are there in the {dept} department?",
    "Who teaches {degree} {short_dept} {sem} semester?",
    "Tell me about the faculty in the {dept} department."
]

fees_templates = [
    "What is the {fee} for {degree} {dept}?",
    "How much is the {fee} for the {sem} semester?",
    "Are there any fee concessions in {fee} for {category} students?",
    "What is the {fee} structure for {degree} First Year?",
    "Does {category} category get relaxation in {fee}?"
]

placements_templates = [
    "What is the average package for {short_dept} students?",
    "Which companies visit for {degree} {dept} placements?",
    "How are the placements for {short_dept}?",
    "Does the college provide internships for {degree} {dept} in {year}?",
    "What was the highest package offered in {short_dept}?"
]

all_questions = set()

def add_permutations(templates, **kwargs):
    keys = kwargs.keys()
    values = kwargs.values()
    for combination in itertools.product(*values):
        mapping = dict(zip(keys, combination))
        for template in templates:
            all_questions.add(template.format(**mapping))

# Generate combinations
add_permutations(admissions_templates, degree=degrees, dept=departments, category=student_categories, short_dept=short_depts)
add_permutations(courses_templates, degree=degrees, dept=departments, sem=semesters, short_dept=short_depts, year=years)
add_permutations(faculty_templates, dept=departments, short_dept=short_depts, degree=degrees, sem=semesters)
add_permutations(fees_templates, fee=fees_aspects, degree=degrees, dept=departments, sem=semesters, category=student_categories)
add_permutations(placements_templates, short_dept=short_depts, degree=degrees, dept=departments, year=years)

# Adding variations to reach 100k
question_prefixes = ["Can you tell me ", "Do you know ", "I would like to know ", "Please explain ", "What details can you give about ", "Share info on "]

extended_questions = set(all_questions)

for q in all_questions:
    if len(extended_questions) >= 105000:
        break
    prefix = random.choice(question_prefixes)
    if q.startswith("What is ") or q.startswith("Who is "):
        extended_questions.add(prefix + q[0].lower() + q[1:])
    elif q.startswith("Are there "):
        extended_questions.add(prefix + "if there are " + q[10:])
    elif q.startswith("How much "):
        extended_questions.add(prefix + q[0].lower() + q[1:])
    elif q.startswith("Does "):
        extended_questions.add(prefix + "if " + q[5:].replace(" get ", " gets ").replace(" provide ", " provides "))
    elif q.startswith("Is there "):
        extended_questions.add(prefix + "if there is " + q[9:])
    else:
        extended_questions.add(prefix + q[0].lower() + q[1:])

final_questions = list(extended_questions)[:100000]

with open("data/generated_100k_questions.txt", "w") as f:
    for q in final_questions:
        f.write(q + "\n")

print(f"Successfully generated {len(final_questions)} questions.")

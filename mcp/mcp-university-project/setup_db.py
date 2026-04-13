# setup_university_db.py
import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

# Setup
fake = Faker("en_US")
conn = sqlite3.connect("university.db")
cursor = conn.cursor()

# ── Create tables ────────────────────────────────────────────────────────────

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    email TEXT,
    phone TEXT,
    date_of_birth TEXT,
    enrollment_date TEXT,
    department TEXT,
    year_of_study INTEGER,
    gpa REAL,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    department TEXT,
    credits INTEGER,
    instructor TEXT,
    max_capacity INTEGER,
    schedule TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    course_id INTEGER,
    enrolled_on TEXT,
    grade TEXT,
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(course_id)  REFERENCES courses(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS professors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    email TEXT,
    department TEXT,
    designation TEXT,
    phone TEXT,
    joined_on TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    title TEXT,
    due_date TEXT,
    max_marks INTEGER,
    FOREIGN KEY(course_id) REFERENCES courses(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER,
    student_id INTEGER,
    submitted_on TEXT,
    marks_obtained INTEGER,
    feedback TEXT,
    FOREIGN KEY(assignment_id) REFERENCES assignments(id),
    FOREIGN KEY(student_id)    REFERENCES students(id)
)
""")

# ── Reference data ───────────────────────────────────────────────────────────

DEPARTMENTS = [
    "Computer Science",
    "Business Administration",
    "Mechanical Engineering",
    "Psychology",
    "Data Science",
]

DESIGNATIONS = ["Assistant Professor", "Associate Professor", "Professor", "Lecturer"]

GRADES = ["A+", "A", "B+", "B", "C+", "C", "D", "F"]

SCHEDULES = [
    "Mon/Wed 09:00-10:30",
    "Tue/Thu 11:00-12:30",
    "Mon/Wed/Fri 14:00-15:00",
    "Tue/Thu 15:00-16:30",
    "Fri 10:00-13:00",
]

COURSE_TITLES = [
    "Introduction to Programming",
    "Data Structures & Algorithms",
    "Database Management Systems",
    "Machine Learning Fundamentals",
    "Business Communication",
    "Financial Accounting",
    "Marketing Principles",
    "Thermodynamics",
    "Fluid Mechanics",
    "Cognitive Psychology",
    "Research Methods",
    "Statistics for Data Science",
    "Cloud Computing",
    "Software Engineering",
    "Organisational Behaviour",
]

# ── Generate professors ──────────────────────────────────────────────────────

professors_data = []
for i in range(20):
    name = fake.name()
    email = fake.company_email()
    department = random.choice(DEPARTMENTS)
    designation = random.choice(DESIGNATIONS)
    phone = fake.phone_number()
    joined_on = fake.date_between(start_date="-15y", end_date="-1y").isoformat()
    professors_data.append((name, email, department, designation, phone, joined_on))

cursor.executemany("""
INSERT OR IGNORE INTO professors (name, email, department, designation, phone, joined_on)
VALUES (?, ?, ?, ?, ?, ?)
""", professors_data)

cursor.execute("SELECT id, name FROM professors")
professor_ids = {name: id_ for id_, name in cursor.fetchall()}
professor_names = list(professor_ids.keys())

# ── Generate courses ─────────────────────────────────────────────────────────

courses_data = []
used_titles = random.sample(COURSE_TITLES, min(15, len(COURSE_TITLES)))
for i, title in enumerate(used_titles):
    code = f"CS{100 + i * 10}"
    department = random.choice(DEPARTMENTS)
    credits = random.choice([2, 3, 4])
    instructor = random.choice(professor_names)
    max_capacity = random.randint(30, 80)
    schedule = random.choice(SCHEDULES)
    courses_data.append((code, title, department, credits, instructor, max_capacity, schedule))

cursor.executemany("""
INSERT OR IGNORE INTO courses (code, title, department, credits, instructor, max_capacity, schedule)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", courses_data)

cursor.execute("SELECT id FROM courses")
course_ids = [row[0] for row in cursor.fetchall()]

# ── Generate students ────────────────────────────────────────────────────────

students_data = []
for _ in range(100):
    name = fake.name()
    email = fake.email()
    phone = fake.phone_number()
    dob = fake.date_of_birth(minimum_age=17, maximum_age=28).isoformat()
    enrollment_date = fake.date_between(start_date="-4y", end_date="-1m").isoformat()
    department = random.choice(DEPARTMENTS)
    year_of_study = random.randint(1, 4)
    gpa = round(random.uniform(1.5, 4.0), 2)
    status = random.choice(["Active", "Active", "Active", "On Leave", "Graduated"])
    students_data.append((name, email, phone, dob, enrollment_date, department, year_of_study, gpa, status))

cursor.executemany("""
INSERT OR IGNORE INTO students (name, email, phone, date_of_birth, enrollment_date,
                                department, year_of_study, gpa, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", students_data)

cursor.execute("SELECT id FROM students")
student_ids = [row[0] for row in cursor.fetchall()]

# ── Generate enrollments ─────────────────────────────────────────────────────

enrollments_data = []
for student_id in student_ids:
    enrolled_courses = random.sample(course_ids, k=random.randint(3, 6))
    for course_id in enrolled_courses:
        enrolled_on = fake.date_between(start_date="-1y", end_date="-1m").isoformat()
        grade = random.choice(GRADES)
        enrollments_data.append((student_id, course_id, enrolled_on, grade))

cursor.executemany("""
INSERT INTO enrollments (student_id, course_id, enrolled_on, grade)
VALUES (?, ?, ?, ?)
""", enrollments_data)

# ── Generate assignments ─────────────────────────────────────────────────────

assignments_data = []
for course_id in course_ids:
    for j in range(random.randint(2, 4)):
        title = f"Assignment {j + 1} — {fake.bs().title()}"
        due_date = (datetime.now() + timedelta(days=random.randint(-30, 60))).date().isoformat()
        max_marks = random.choice([50, 100])
        assignments_data.append((course_id, title, due_date, max_marks))

cursor.executemany("""
INSERT INTO assignments (course_id, title, due_date, max_marks)
VALUES (?, ?, ?, ?)
""", assignments_data)

cursor.execute("SELECT id, max_marks FROM assignments")
assignment_rows = cursor.fetchall()

# ── Generate submissions ─────────────────────────────────────────────────────

submissions_data = []
for assignment_id, max_marks in assignment_rows:
    # Random subset of students submit each assignment
    submitting_students = random.sample(student_ids, k=random.randint(10, 30))
    for student_id in submitting_students:
        submitted_on = fake.date_between(start_date="-30d", end_date="today").isoformat()
        marks_obtained = random.randint(int(max_marks * 0.3), max_marks)
        feedback = random.choice([
            "Good work, keep it up.",
            "Needs more detail in the analysis.",
            "Excellent understanding of the topic.",
            "Please revise and resubmit.",
            "Well structured and clearly argued.",
            "Missing references — please add citations.",
        ])
        submissions_data.append((assignment_id, student_id, submitted_on, marks_obtained, feedback))

cursor.executemany("""
INSERT INTO submissions (assignment_id, student_id, submitted_on, marks_obtained, feedback)
VALUES (?, ?, ?, ?, ?)
""", submissions_data)

# ── Commit and close ─────────────────────────────────────────────────────────

conn.commit()
conn.close()

print("✅ University database successfully created with:")
print(f"   👨‍🎓 100 students")
print(f"   📚 {len(courses_data)} courses")
print(f"   👨‍🏫 {len(professors_data)} professors")
print(f"   📝 {len(assignments_data)} assignments")
print(f"   📬 {len(submissions_data)} submissions")
print(f"   🎓 {len(enrollments_data)} enrollments")

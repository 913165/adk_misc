# University Management Agent — Prompts & SQL Queries

> Ready-to-use natural language prompts and their matching SQLite queries.  
> Database: `university.db` · Tables: `students`, `professors`, `courses`, `enrollments`, `assignments`, `submissions`

---

## Table of Contents

- [Students](#students)
- [Professors](#professors)
- [Courses](#courses)
- [Enrollments & Grades](#enrollments--grades)
- [Assignments & Submissions](#assignments--submissions)
- [Analytics & Insights](#analytics--insights)
- [Data Integrity Checks](#data-integrity-checks)

---

## Students

**"Show me the top 10 students by GPA"**
```sql
SELECT name, department, year_of_study, gpa, status
FROM students
ORDER BY gpa DESC
LIMIT 10;
```

---

**"List all students in the Computer Science department"**
```sql
SELECT name, email, year_of_study, gpa, status
FROM students
WHERE department = 'Computer Science'
ORDER BY year_of_study, name;
```

---

**"Which students are currently on leave?"**
```sql
SELECT name, email, department, year_of_study
FROM students
WHERE status = 'On Leave'
ORDER BY department;
```

---

**"How many students are enrolled in each department?"**
```sql
SELECT department,
       COUNT(*)                        AS total_students,
       ROUND(AVG(gpa), 2)              AS avg_gpa,
       SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active
FROM students
GROUP BY department
ORDER BY total_students DESC;
```

---

**"Find all students with GPA below 2.0 — at risk"**
```sql
SELECT name, email, department, year_of_study, gpa
FROM students
WHERE gpa < 2.0
ORDER BY gpa ASC;
```

---

**"Show me students in their final year (year 4)"**
```sql
SELECT name, email, department, gpa, status
FROM students
WHERE year_of_study = 4
ORDER BY department, gpa DESC;
```

---

**"List students who have already graduated"**
```sql
SELECT name, email, department, gpa
FROM students
WHERE status = 'Graduated'
ORDER BY gpa DESC;
```

---

## Professors

**"List all professors and their departments"**
```sql
SELECT name, designation, department, email
FROM professors
ORDER BY department, designation;
```

---

**"Which professors joined more than 10 years ago?"**
```sql
SELECT name, department, designation, joined_on
FROM professors
WHERE DATE(joined_on) <= DATE('now', '-10 years')
ORDER BY joined_on ASC;
```

---

**"How many professors are in each department?"**
```sql
SELECT department,
       COUNT(*) AS total_professors
FROM professors
GROUP BY department
ORDER BY total_professors DESC;
```

---

**"Show me all Associate Professors"**
```sql
SELECT name, department, email, phone, joined_on
FROM professors
WHERE designation = 'Associate Professor'
ORDER BY department;
```

---

**"Which professor teaches the most courses?"**
```sql
SELECT p.name, p.department, COUNT(c.id) AS course_count
FROM professors p
JOIN courses c ON c.instructor = p.name
GROUP BY p.name, p.department
ORDER BY course_count DESC
LIMIT 5;
```

---

## Courses

**"List all courses with their credits and schedule"**
```sql
SELECT code, title, department, credits, instructor, schedule, max_capacity
FROM courses
ORDER BY department, code;
```

---

**"Which courses have the highest enrollment capacity?"**
```sql
SELECT code, title, max_capacity, credits
FROM courses
ORDER BY max_capacity DESC
LIMIT 10;
```

---

**"Which course has the most students enrolled?"**
```sql
SELECT c.code, c.title, c.department,
       COUNT(e.id) AS enrolled_students
FROM courses c
LEFT JOIN enrollments e ON c.id = e.course_id
GROUP BY c.id, c.code, c.title, c.department
ORDER BY enrolled_students DESC
LIMIT 10;
```

---

**"Show me all courses in the Data Science department"**
```sql
SELECT code, title, credits, instructor, schedule, max_capacity
FROM courses
WHERE department = 'Data Science'
ORDER BY code;
```

---

**"Which courses are running at full capacity?"**
```sql
SELECT c.code, c.title, c.max_capacity,
       COUNT(e.id) AS enrolled
FROM courses c
JOIN enrollments e ON c.id = e.course_id
GROUP BY c.id, c.code, c.title, c.max_capacity
HAVING enrolled >= c.max_capacity
ORDER BY c.title;
```

---

## Enrollments & Grades

**"Show me all students enrolled in Database Management Systems"**
```sql
SELECT s.name, s.department, s.year_of_study, e.grade, e.enrolled_on
FROM enrollments e
JOIN students s ON e.student_id = s.id
JOIN courses c  ON e.course_id  = c.id
WHERE c.title = 'Database Management Systems'
ORDER BY e.grade, s.name;
```

---

**"How many students received an A+ grade?"**
```sql
SELECT COUNT(*) AS total_a_plus,
       COUNT(DISTINCT student_id) AS unique_students
FROM enrollments
WHERE grade = 'A+';
```

---

**"What is the grade distribution across all courses?"**
```sql
SELECT grade,
       COUNT(*) AS count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM enrollments), 1) AS percentage
FROM enrollments
GROUP BY grade
ORDER BY count DESC;
```

---

**"List students who failed (grade F) in any course"**
```sql
SELECT DISTINCT s.name, s.email, s.department,
       c.title AS failed_course
FROM enrollments e
JOIN students s ON e.student_id = s.id
JOIN courses c  ON e.course_id  = c.id
WHERE e.grade = 'F'
ORDER BY s.name;
```

---

**"Show average grade per course"**
```sql
SELECT c.title,
       COUNT(e.id) AS enrollments,
       SUM(CASE WHEN e.grade = 'A+' THEN 1 ELSE 0 END) AS a_plus,
       SUM(CASE WHEN e.grade = 'A'  THEN 1 ELSE 0 END) AS a,
       SUM(CASE WHEN e.grade = 'F'  THEN 1 ELSE 0 END) AS fails
FROM courses c
JOIN enrollments e ON c.id = e.course_id
GROUP BY c.id, c.title
ORDER BY a_plus DESC;
```

---

## Assignments & Submissions

**"Which assignments are due in the next 7 days?"**
```sql
SELECT a.title, c.title AS course, a.due_date, a.max_marks
FROM assignments a
JOIN courses c ON a.course_id = c.id
WHERE DATE(a.due_date) BETWEEN DATE('now') AND DATE('now', '+7 days')
ORDER BY a.due_date ASC;
```

---

**"Show me all overdue assignments"**
```sql
SELECT a.title, c.title AS course, a.due_date, a.max_marks
FROM assignments a
JOIN courses c ON a.course_id = c.id
WHERE DATE(a.due_date) < DATE('now')
ORDER BY a.due_date ASC;
```

---

**"Which students have not submitted any assignments?"**
```sql
SELECT s.name, s.email, s.department
FROM students s
LEFT JOIN submissions sub ON s.id = sub.student_id
WHERE sub.id IS NULL
ORDER BY s.department, s.name;
```

---

**"What is the average marks obtained per assignment?"**
```sql
SELECT a.title, c.title AS course,
       a.max_marks,
       COUNT(sub.id)                    AS submissions,
       ROUND(AVG(sub.marks_obtained), 1) AS avg_marks,
       MAX(sub.marks_obtained)           AS highest,
       MIN(sub.marks_obtained)           AS lowest
FROM assignments a
JOIN courses c    ON a.course_id     = c.id
LEFT JOIN submissions sub ON a.id   = sub.assignment_id
GROUP BY a.id, a.title, c.title, a.max_marks
ORDER BY avg_marks DESC;
```

---

**"Show the top 5 submissions with the highest marks"**
```sql
SELECT s.name, a.title AS assignment, c.title AS course,
       sub.marks_obtained, a.max_marks, sub.feedback
FROM submissions sub
JOIN students s    ON sub.student_id    = s.id
JOIN assignments a ON sub.assignment_id = a.id
JOIN courses c     ON a.course_id       = c.id
ORDER BY sub.marks_obtained DESC
LIMIT 5;
```

---

**"Which students submitted an assignment late?"**
```sql
SELECT s.name, a.title AS assignment,
       a.due_date, sub.submitted_on
FROM submissions sub
JOIN students s    ON sub.student_id    = s.id
JOIN assignments a ON sub.assignment_id = a.id
WHERE DATE(sub.submitted_on) > DATE(a.due_date)
ORDER BY sub.submitted_on DESC;
```

---

## Analytics & Insights

**"Which department has the highest average GPA?"**
```sql
SELECT department,
       COUNT(*)             AS students,
       ROUND(AVG(gpa), 2)  AS avg_gpa,
       ROUND(MAX(gpa), 2)  AS top_gpa,
       ROUND(MIN(gpa), 2)  AS lowest_gpa
FROM students
GROUP BY department
ORDER BY avg_gpa DESC;
```

---

**"Show students enrolled in more than 5 courses"**
```sql
SELECT s.name, s.department, s.gpa,
       COUNT(e.id) AS course_count
FROM students s
JOIN enrollments e ON s.id = e.student_id
GROUP BY s.id, s.name, s.department, s.gpa
HAVING course_count > 5
ORDER BY course_count DESC;
```

---

**"Which professor's courses have the best average grades?"**
```sql
SELECT c.instructor,
       COUNT(DISTINCT c.id)  AS courses_taught,
       COUNT(e.id)            AS total_enrollments,
       SUM(CASE WHEN e.grade IN ('A+','A') THEN 1 ELSE 0 END) AS top_grades,
       ROUND(SUM(CASE WHEN e.grade IN ('A+','A') THEN 1.0 ELSE 0 END)
             / COUNT(e.id) * 100, 1)                           AS top_grade_pct
FROM courses c
JOIN enrollments e ON c.id = e.course_id
GROUP BY c.instructor
ORDER BY top_grade_pct DESC;
```

---

**"Give me a full university summary"**
```sql
SELECT
    (SELECT COUNT(*) FROM students)                           AS total_students,
    (SELECT COUNT(*) FROM students WHERE status = 'Active')   AS active_students,
    (SELECT COUNT(*) FROM professors)                         AS total_professors,
    (SELECT COUNT(*) FROM courses)                            AS total_courses,
    (SELECT COUNT(*) FROM enrollments)                        AS total_enrollments,
    (SELECT COUNT(*) FROM assignments)                        AS total_assignments,
    (SELECT COUNT(*) FROM submissions)                        AS total_submissions,
    (SELECT ROUND(AVG(gpa), 2) FROM students)                 AS overall_avg_gpa;
```

---

## Data Integrity Checks

**"Are there any students with no enrollments?"**
```sql
SELECT s.name, s.email, s.department, s.status
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id
WHERE e.id IS NULL
ORDER BY s.department;
```

---

**"Are there courses with no students enrolled?"**
```sql
SELECT c.code, c.title, c.department, c.instructor
FROM courses c
LEFT JOIN enrollments e ON c.id = e.course_id
WHERE e.id IS NULL
ORDER BY c.department;
```

---

**"Are there assignments with no submissions at all?"**
```sql
SELECT a.title, c.title AS course, a.due_date, a.max_marks
FROM assignments a
JOIN courses c ON a.course_id = c.id
LEFT JOIN submissions sub ON a.id = sub.assignment_id
WHERE sub.id IS NULL
ORDER BY a.due_date;
```

---

**"Show duplicate student emails if any"**
```sql
SELECT email, COUNT(*) AS count
FROM students
GROUP BY email
HAVING count > 1
ORDER BY count DESC;
```

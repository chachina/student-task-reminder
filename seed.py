"""Seed demo data into Neon Postgres."""
import psycopg2
import os
from datetime import date, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

DEMO_STUDENTS = [
    ("Faith Wanjiku", "Zetech/2024/001", "faith@zetech.ac.ke", "Computer Science", "Year 2", "faith123"),
    ("Brian Ochieng", "Zetech/2024/002", "brian@zetech.ac.ke", "Information Technology", "Year 2", "brian123"),
    ("Mercy Chebet",  "Zetech/2024/003", "mercy@zetech.ac.ke",  "Business Administration", "Year 1", "mercy123"),
]

TODAY = date.today()

DEMO_TASKS = [
    # Faith's tasks
    (1, "Submit DIT Project Proposal",    "Write and submit the project proposal document",  (TODAY + timedelta(days=2)).isoformat(),  "Pending"),
    (1, "Complete Python Assignment",     "Finish the Flask routing exercises",              (TODAY + timedelta(days=-1)).isoformat(), "Pending"),
    (1, "Database Normalization Quiz",    "Review 1NF, 2NF, 3NF forms",                     (TODAY + timedelta(days=5)).isoformat(),  "Pending"),
    (1, "Read Chapter 7 - Networking",   "OSI Model and TCP/IP layers",                     (TODAY + timedelta(days=7)).isoformat(),  "Pending"),
    (1, "Attend Career Fair",              "University annual career expo",                   (TODAY + timedelta(days=3)).isoformat(),  "Completed"),
    (1, "Group Project Meeting",          "Discuss project分工 with teammates",              (TODAY + timedelta(days=1)).isoformat(),  "Pending"),
    # Brian's tasks
    (2, "Submit Networking Report",       "10-page report on LAN setups",                     (TODAY + timedelta(days=4)).isoformat(),  "Pending"),
    (2, "JavaScript Midterm Exam",        "DOM manipulation and ES6 features",               (TODAY + timedelta(days=6)).isoformat(),  "Pending"),
    (2, "Complete Internship Application","Upload CV and cover letter",                       (TODAY + timedelta(days=-2)).isoformat(), "Pending"),
]


def run(get_db_fn=None):
    if get_db_fn is None:
        conn = psycopg2.connect(DATABASE_URL)
    else:
        conn = get_db_fn()

    cur = conn.cursor()

    for s in DEMO_STUDENTS:
        cur.execute(
            """INSERT INTO students (full_name, registration_no, email, course, year_of_study, password)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO NOTHING""",
            s,
        )

    for t in DEMO_TASKS:
        cur.execute(
            """INSERT INTO tasks (student_id, task_title, task_description, due_date, status)
               VALUES (%s, %s, %s, %s, %s)""",
            t,
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Seed data inserted.")


if __name__ == "__main__":
    run()

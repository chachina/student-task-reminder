"""
Student Academic Planner System — In-Memory Version
No database. Works on Render free tier without Postgres.
"""
import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "student-planner-secret-key-change-me")

# ---------------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------------
students_db = {}
next_student_id = 1

tasks_db = {}
next_task_id = 1

# Seed demo student + tasks
DEMO_TODAY = date.today()
DEMO_TASKS = [
    ("Submit DIT Project Proposal",   "Write and submit the project proposal",           (DEMO_TODAY + timedelta(days=2)).isoformat(),  "Pending"),
    ("Complete Python Assignment",     "Flask routing exercises",                         (DEMO_TODAY + timedelta(days=-1)).isoformat(), "Pending"),
    ("Database Normalization Quiz",   "Review 1NF, 2NF, 3NF",                          (DEMO_TODAY + timedelta(days=5)).isoformat(),  "Pending"),
    ("Read Chapter 7 - Networking",  "OSI Model and TCP/IP layers",                    (DEMO_TODAY + timedelta(days=7)).isoformat(),  "Pending"),
    ("Attend Career Fair",            "University annual career expo",                   (DEMO_TODAY + timedelta(days=3)).isoformat(),  "Completed"),
    ("Group Project Meeting",         "Discuss project with teammates",                  (DEMO_TODAY + timedelta(days=1)).isoformat(),  "Pending"),
]

students_db[1] = {
    "student_id": 1,
    "full_name": "Faith Wanjiku",
    "registration_no": "Zetech/2024/001",
    "email": "faith@zetech.ac.ke",
    "course": "Computer Science",
    "year_of_study": "Year 2",
    "password": "faith123",
}
for title, desc, due, status in DEMO_TASKS:
    tasks_db[next_task_id] = {
        "task_id": next_task_id, "student_id": 1,
        "task_title": title, "task_description": desc,
        "due_date": due, "status": status
    }
    next_task_id += 1
next_student_id = 2


def get_tasks_for_student(student_id):
    return [t for t in tasks_db.values() if t["student_id"] == student_id]


def login_required():
    return "student_id" not in session


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    global next_student_id
    message = None
    if request.method == "POST" and "register" in request.form:
        full_name = request.form.get("full_name", "").strip()
        registration_no = request.form.get("registration_no", "").strip()
        email = request.form.get("email", "").strip().lower()
        course = request.form.get("course", "").strip()
        year_of_study = request.form.get("year_of_study", "").strip()
        password = request.form.get("password", "").strip()

        if not full_name or not email or not password:
            message = "All fields are required."
        elif any(s["email"] == email for s in students_db.values()):
            message = "An account with that email already exists."
        else:
            students_db[next_student_id] = {
                "student_id": next_student_id,
                "full_name": full_name,
                "registration_no": registration_no,
                "email": email,
                "course": course,
                "year_of_study": year_of_study,
                "password": password,
            }
            next_student_id += 1
            message = "Registration Successful! Please log in."

    return render_template("register.html", message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST" and "login" in request.form:
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        student = next((s for s in students_db.values() if s["email"] == email and s["password"] == password), None)
        if student:
            session["student_id"] = student["student_id"]
            session["full_name"] = student["full_name"]
            return redirect(url_for("student_dashboard"))
        else:
            error = "Invalid email or password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if login_required():
        return redirect(url_for("login"))
    return render_template("student/dashboard_simple.html", full_name=session.get("full_name"))


# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------
@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if login_required():
        return redirect(url_for("login"))
    global next_task_id
    error = None
    if request.method == "POST" and "add_task" in request.form:
        task_title = request.form.get("task_title", "").strip()
        due_date = request.form.get("due_date", "").strip()
        task_description = request.form.get("task_description", "").strip()
        if not task_title or not due_date:
            error = "Task title and due date are required."
        else:
            tasks_db[next_task_id] = {
                "task_id": next_task_id, "student_id": session["student_id"],
                "task_title": task_title, "task_description": task_description,
                "due_date": due_date, "status": "Pending"
            }
            next_task_id += 1
            return redirect(url_for("student_dashboard"))
    prefill = request.args.get("date", "")
    return render_template("add_task.html", error=error, prefill_date=prefill)


@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if login_required():
        return redirect(url_for("login"))
    task = tasks_db.get(task_id)
    if not task or task["student_id"] != session["student_id"]:
        return redirect(url_for("student_dashboard"))
    if request.method == "POST" and "update_task" in request.form:
        tasks_db[task_id]["task_title"] = request.form.get("task_title", "")
        tasks_db[task_id]["task_description"] = request.form.get("description", "")
        tasks_db[task_id]["due_date"] = request.form.get("due_date", "")
        tasks_db[task_id]["status"] = request.form.get("status", "Pending")
        return redirect(url_for("student_dashboard", updated=1))
    return render_template("edit_task.html", task=task)


@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    if login_required():
        return redirect(url_for("login"))
    if task_id in tasks_db and tasks_db[task_id]["student_id"] == session["student_id"]:
        del tasks_db[task_id]
    return redirect(url_for("student_dashboard"))


@app.route("/events")
def events():
    """JSON feed for FullCalendar."""
    today = date.today().isoformat()
    out = []
    for t in tasks_db.values():
        if t["status"] == "Completed":
            color = "#16a34a"
        elif t["due_date"] < today:
            color = "#dc2626"
        else:
            color = "#2563eb"
        out.append({"id": t["task_id"], "title": t["task_title"], "start": t["due_date"], "color": color})
    return jsonify(out)


# ---------------------------------------------------------------------------
# Student area
# ---------------------------------------------------------------------------
@app.route("/student/dashboard", methods=["GET", "POST"])
def student_dashboard():
    if login_required():
        return redirect(url_for("login"))
    global next_task_id
    sid = session["student_id"]

    if request.method == "POST" and "task_title" in request.form:
        task_title = request.form.get("task_title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        if task_title and due_date:
            tasks_db[next_task_id] = {
                "task_id": next_task_id, "student_id": sid,
                "task_title": task_title, "task_description": description,
                "due_date": due_date, "status": "Pending"
            }
            next_task_id += 1
            return jsonify({"success": True, "message": "Task added successfully!"})
        return jsonify({"success": False, "message": "Please fill in required fields."})

    my_tasks = get_tasks_for_student(sid)
    return render_template(
        "student/dashboard.html",
        full_name=session.get("full_name"),
        total=len(my_tasks),
        pending=sum(1 for t in my_tasks if t["status"] == "Pending"),
        completed=sum(1 for t in my_tasks if t["status"] == "Completed"),
        tasks=my_tasks,
    )


@app.route("/student/calendar", methods=["GET", "POST"])
def student_calendar():
    if login_required():
        return redirect(url_for("login"))
    global next_task_id
    sid = session["student_id"]

    if request.method == "POST" and "task_title" in request.form and "update_task" not in request.form:
        task_title = request.form.get("task_title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        if task_title and due_date:
            tasks_db[next_task_id] = {
                "task_id": next_task_id, "student_id": sid,
                "task_title": task_title, "task_description": description,
                "due_date": due_date, "status": "Pending"
            }
            next_task_id += 1
            return jsonify({"success": True, "message": "Task added successfully!"})
        return jsonify({"success": False, "message": "Please fill in required fields."})

    if request.method == "GET" and "fetch_task" in request.args:
        task = tasks_db.get(int(request.args.get("fetch_task")))
        if task and task["student_id"] == sid:
            return jsonify({"success": True, "task": task})
        return jsonify({"success": False, "message": "Task not found."})

    if request.method == "POST" and "update_task" in request.form:
        tid = int(request.form.get("task_id", 0))
        if tid in tasks_db and tasks_db[tid]["student_id"] == sid:
            tasks_db[tid]["task_title"] = request.form.get("task_title", "")
            tasks_db[tid]["task_description"] = request.form.get("description", "")
            tasks_db[tid]["due_date"] = request.form.get("due_date", "")
            tasks_db[tid]["status"] = request.form.get("status", "Pending")
            return jsonify({"success": True, "message": "Task updated!"})
        return jsonify({"success": False, "message": "Task not found."})

    return render_template("student/calendar.html")


@app.route("/student/notifications", methods=["GET", "POST"])
def student_notifications():
    if login_required():
        return redirect(url_for("login"))
    global next_task_id
    sid = session["student_id"]
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    if request.method == "POST" and "update_task" in request.form:
        tid = int(request.form.get("task_id", 0))
        if tid in tasks_db and tasks_db[tid]["student_id"] == sid:
            tasks_db[tid]["task_title"] = request.form.get("task_title", "")
            tasks_db[tid]["task_description"] = request.form.get("description", "")
            tasks_db[tid]["due_date"] = request.form.get("due_date", "")
            tasks_db[tid]["status"] = request.form.get("status", "Pending")
            return jsonify({"success": True, "message": "Task updated!"})
        return jsonify({"success": False, "message": "Error."})

    if request.method == "GET" and "fetch_task" in request.args:
        task = tasks_db.get(int(request.args.get("fetch_task")))
        if task and task["student_id"] == sid:
            return jsonify({"success": True, "task": task})
        return jsonify({"success": False, "message": "Task not found."})

    notifications = []
    has_overdue = has_due_today = has_due_tomorrow = False
    for t in tasks_db.values():
        if t["student_id"] != sid or t["status"] == "Completed":
            continue
        if t["due_date"] < today:
            notifications.append({**t, "css_class": "notification-overdue", "icon": "🔴", "message": "OVERDUE"})
            has_overdue = True
        elif t["due_date"] == today:
            notifications.append({**t, "css_class": "notification-today", "icon": "🟡", "message": "DUE TODAY"})
            has_due_today = True
        elif t["due_date"] == tomorrow:
            notifications.append({**t, "css_class": "notification-tomorrow", "icon": "🟢", "message": "DUE TOMORROW"})
            has_due_tomorrow = True

    return render_template(
        "student/notifications.html",
        notifications=notifications,
        has_overdue=has_overdue, has_due_today=has_due_today, has_due_tomorrow=has_due_tomorrow,
    )


@app.route("/student/profile")
def student_profile():
    if login_required():
        return redirect(url_for("login"))
    student = students_db.get(session["student_id"], {})
    return render_template("student/profile.html", student=student)


@app.route("/student/edit_profile", methods=["GET", "POST"])
def student_edit_profile():
    if login_required():
        return redirect(url_for("login"))
    sid = session["student_id"]
    student = students_db.get(sid, {})
    updated = False
    if request.method == "POST" and "update" in request.form:
        students_db[sid]["full_name"] = request.form.get("full_name", "")
        students_db[sid]["email"] = request.form.get("email", "")
        students_db[sid]["course"] = request.form.get("course", "")
        students_db[sid]["year_of_study"] = request.form.get("year_of_study", "")
        session["full_name"] = students_db[sid]["full_name"]
        updated = True
        student = students_db[sid]
    return render_template("student/edit_profile.html", student=student, updated=updated)


@app.route("/student/reports")
def student_reports():
    if login_required():
        return redirect(url_for("login"))
    sid = session["student_id"]
    today = date.today().isoformat()
    my_tasks = get_tasks_for_student(sid)
    total = len(my_tasks)
    pending = sum(1 for t in my_tasks if t["status"] == "Pending")
    completed = sum(1 for t in my_tasks if t["status"] == "Completed")
    overdue = sum(1 for t in my_tasks if t["status"] == "Pending" and t["due_date"] < today)
    return render_template("student/reports.html", total=total, pending=pending, completed=completed, overdue=overdue)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

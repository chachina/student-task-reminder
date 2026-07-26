"""
Student Academic Planner System
--------------------------------
Flask + Neon Postgres rebuild of the original PHP + MySQL project.

Same pages, same look, same behaviour:
  - Register / Login / Logout
  - Student dashboard with mini calendar + task table (AJAX add task)
  - Full calendar page (FullCalendar) with AJAX add/edit task
  - Notifications page (overdue / due today / due tomorrow) with sound alert
  - Profile / Edit profile
  - Reports page with a pie chart (Chart.js)
  - events.php -> /events JSON feed for the calendar
  - add_task / edit_task / delete_task

Run with:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000/
"""
import os
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, session, jsonify

from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "student-planner-secret-key-change-me")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_required_redirect():
    """Mirrors the PHP `if(!isset($_SESSION['student_id'])){ header(...); }` guard."""
    return "student_id" not in session


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    message = None

    if request.method == "POST" and "register" in request.form:
        full_name = request.form.get("full_name", "")
        registration_no = request.form.get("registration_no", "")
        email = request.form.get("email", "")
        course = request.form.get("course", "")
        year_of_study = request.form.get("year_of_study", "")
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO students
                   (full_name, registration_no, email, course, year_of_study, password)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (full_name, registration_no, email, course, year_of_study, password),
            )
            db.commit()
            message = "Registration Successful!"
        except Exception:
            message = "Registration Failed!"
        finally:
            cur.close()
            db.close()

    return render_template("register.html", message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST" and "login" in request.form:
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT * FROM students WHERE email = %s AND password = %s",
            (email, password),
        )
        student = cur.fetchone()
        cur.close()
        db.close()

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
    # Legacy simple welcome page (kept for parity with the original dashboard.php)
    if login_required_redirect():
        return redirect(url_for("login"))
    return render_template("student/dashboard_simple.html", full_name=session.get("full_name"))


# ---------------------------------------------------------------------------
# Task management (root-level, matches add_task.php / edit_task.php / delete_task.php)
# ---------------------------------------------------------------------------
@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if login_required_redirect():
        return redirect(url_for("login"))

    error = None

    if request.method == "POST" and "add_task" in request.form:
        student_id = session["student_id"]
        task_title = request.form.get("task_title", "").strip()
        task_description = request.form.get("task_description", "").strip()
        due_date = request.form.get("due_date", "")

        if task_title == "" or due_date == "":
            error = "Please fill in the task title and due date."
        else:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                """INSERT INTO tasks (student_id, task_title, task_description, due_date)
                   VALUES (%s, %s, %s, %s)""",
                (student_id, task_title, task_description, due_date),
            )
            db.commit()
            cur.close()
            db.close()
            return redirect(url_for("student_dashboard"))

    prefill_date = request.args.get("date", "")
    return render_template("add_task.html", error=error, prefill_date=prefill_date)


@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if login_required_redirect():
        return redirect(url_for("login"))

    student_id = session["student_id"]
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT * FROM tasks WHERE task_id = %s AND student_id = %s",
        (task_id, student_id),
    )
    task = cur.fetchone()

    if not task:
        cur.close()
        db.close()
        return redirect(url_for("student_dashboard"))

    if request.method == "POST" and "update_task" in request.form:
        task_title = request.form.get("task_title", "")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        status = request.form.get("status", "")

        cur.execute(
            """UPDATE tasks SET task_title = %s, task_description = %s,
               due_date = %s, status = %s WHERE task_id = %s AND student_id = %s""",
            (task_title, description, due_date, status, task_id, student_id),
        )
        db.commit()
        cur.close()
        db.close()
        return redirect(url_for("student_dashboard", updated=1))

    cur.close()
    db.close()
    return render_template("edit_task.html", task=task)


@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    if login_required_redirect():
        return redirect(url_for("login"))

    student_id = session["student_id"]
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "DELETE FROM tasks WHERE task_id = %s AND student_id = %s",
        (task_id, student_id),
    )
    db.commit()
    cur.close()
    db.close()
    return redirect(url_for("student_dashboard"))


@app.route("/events")
def events():
    """JSON feed for FullCalendar (equivalent of events.php)."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT task_id, task_title, due_date, status FROM tasks"
    )
    rows = cur.fetchall()
    cur.close()
    db.close()

    today = date.today().isoformat()
    out = []
    for row in rows:
        if row["status"] == "Completed":
            color = "#16a34a"  # Green
        elif row["due_date"] < today:
            color = "#dc2626"  # Red (overdue)
        else:
            color = "#2563eb"  # Blue (pending)

        out.append(
            {
                "id": row["task_id"],
                "title": row["task_title"],
                "start": row["due_date"],
                "color": color,
            }
        )

    return jsonify(out)


# ---------------------------------------------------------------------------
# Student area (matches the /student/*.php pages)
# ---------------------------------------------------------------------------
@app.route("/student/dashboard", methods=["GET", "POST"])
def student_dashboard():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    student_id = session["student_id"]

    # AJAX task addition (same behaviour as the PHP inline handler)
    if request.method == "POST" and "task_title" in request.form:
        task_title = request.form.get("task_title", "")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        try:
            cur.execute(
                """INSERT INTO tasks (student_id, task_title, task_description, due_date, status)
                   VALUES (%s, %s, %s, %s, 'Pending')""",
                (student_id, task_title, description, due_date),
            )
            db.commit()
            cur.close()
            db.close()
            return jsonify({"success": True, "message": "Task added successfully!"})
        except Exception:
            cur.close()
            db.close()
            return jsonify({"success": False, "message": "Error adding task"})

    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s", (student_id,)
    )
    total = cur.fetchone()["c"]
    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s AND status = 'Pending'",
        (student_id,),
    )
    pending = cur.fetchone()["c"]
    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s AND status = 'Completed'",
        (student_id,),
    )
    completed = cur.fetchone()["c"]

    cur.execute(
        """SELECT task_id, task_title, task_description, due_date, status
           FROM tasks WHERE student_id = %s ORDER BY due_date ASC""",
        (student_id,),
    )
    tasks = cur.fetchall()
    cur.close()
    db.close()

    return render_template(
        "student/dashboard.html",
        full_name=session.get("full_name"),
        total=total,
        pending=pending,
        completed=completed,
        tasks=tasks,
    )


@app.route("/student/calendar", methods=["GET", "POST"])
def student_calendar():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    student_id = session["student_id"]

    # AJAX task addition
    if request.method == "POST" and "task_title" in request.form and "update_task" not in request.form:
        task_title = request.form.get("task_title", "")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        try:
            cur.execute(
                """INSERT INTO tasks (student_id, task_title, task_description, due_date, status)
                   VALUES (%s, %s, %s, %s, 'Pending')""",
                (student_id, task_title, description, due_date),
            )
            db.commit()
            cur.close()
            db.close()
            return jsonify({"success": True, "message": "Task added successfully!"})
        except Exception:
            cur.close()
            db.close()
            return jsonify({"success": False, "message": "Error adding task"})

    # AJAX task fetch for editing
    if request.method == "GET" and "fetch_task" in request.args:
        task_id = request.args.get("fetch_task")
        cur.execute(
            "SELECT * FROM tasks WHERE task_id = %s AND student_id = %s",
            (task_id, student_id),
        )
        task = cur.fetchone()
        cur.close()
        db.close()
        if task:
            return jsonify({"success": True, "task": dict(task)})
        return jsonify({"success": False, "message": "Task not found"})

    # AJAX task update
    if request.method == "POST" and "update_task" in request.form:
        task_id = request.form.get("task_id", "")
        task_title = request.form.get("task_title", "")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        status = request.form.get("status", "")
        try:
            cur.execute(
                """UPDATE tasks SET task_title = %s, task_description = %s, due_date = %s,
                   status = %s WHERE task_id = %s AND student_id = %s""",
                (task_title, description, due_date, status, task_id, student_id),
            )
            db.commit()
            cur.close()
            db.close()
            return jsonify({"success": True, "message": "Task updated successfully!"})
        except Exception:
            cur.close()
            db.close()
            return jsonify({"success": False, "message": "Error updating task"})

    cur.close()
    db.close()
    return render_template("student/calendar.html")


@app.route("/student/notifications", methods=["GET", "POST"])
def student_notifications():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    student_id = session["student_id"]
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # AJAX task fetch for editing
    if request.method == "GET" and "fetch_task" in request.args:
        task_id = request.args.get("fetch_task")
        cur.execute(
            "SELECT * FROM tasks WHERE task_id = %s AND student_id = %s",
            (task_id, student_id),
        )
        task = cur.fetchone()
        cur.close()
        db.close()
        if task:
            return jsonify({"success": True, "task": dict(task)})
        return jsonify({"success": False, "message": "Task not found"})

    # AJAX task update
    if request.method == "POST" and "update_task" in request.form:
        task_id = request.form.get("task_id", "")
        task_title = request.form.get("task_title", "")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        status = request.form.get("status", "")
        try:
            cur.execute(
                """UPDATE tasks SET task_title = %s, task_description = %s, due_date = %s,
                   status = %s WHERE task_id = %s AND student_id = %s""",
                (task_title, description, due_date, status, task_id, student_id),
            )
            db.commit()
            cur.close()
            db.close()
            return jsonify({"success": True, "message": "Task updated successfully!"})
        except Exception:
            cur.close()
            db.close()
            return jsonify({"success": False, "message": "Error updating task"})

    cur.execute(
        """SELECT task_id, task_title, task_description, due_date, status
           FROM tasks WHERE student_id = %s ORDER BY due_date ASC""",
        (student_id,),
    )
    rows = cur.fetchall()
    cur.close()
    db.close()

    notifications = []
    has_overdue = has_due_today = has_due_tomorrow = False

    for task in rows:
        if task["status"] == "Completed":
            continue

        if task["due_date"] < today:
            css_class, icon, message = "notification-overdue", "🔴", "OVERDUE"
            has_overdue = True
        elif task["due_date"] == today:
            css_class, icon, message = "notification-today", "🟡", "DUE TODAY"
            has_due_today = True
        elif task["due_date"] == tomorrow:
            css_class, icon, message = "notification-tomorrow", "🟢", "DUE TOMORROW"
            has_due_tomorrow = True
        else:
            continue

        notifications.append(
            {
                "task_id": task["task_id"],
                "task_title": task["task_title"],
                "due_date": task["due_date"],
                "css_class": css_class,
                "icon": icon,
                "message": message,
            }
        )

    return render_template(
        "student/notifications.html",
        notifications=notifications,
        has_overdue=has_overdue,
        has_due_today=has_due_today,
        has_due_tomorrow=has_due_tomorrow,
    )


@app.route("/student/profile")
def student_profile():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM students WHERE student_id = %s", (session["student_id"],)
    )
    student = cur.fetchone()
    cur.close()
    db.close()

    return render_template("student/profile.html", student=student)


@app.route("/student/edit_profile", methods=["GET", "POST"])
def student_edit_profile():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    student_id = session["student_id"]
    cur.execute(
        "SELECT * FROM students WHERE student_id = %s", (student_id,)
    )
    student = cur.fetchone()

    updated = False

    if request.method == "POST" and "update" in request.form:
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        course = request.form.get("course", "")
        year_of_study = request.form.get("year_of_study", "")

        cur.execute(
            """UPDATE students SET full_name = %s, email = %s, course = %s, year_of_study = %s
               WHERE student_id = %s""",
            (full_name, email, course, year_of_study, student_id),
        )
        db.commit()

        session["full_name"] = full_name
        updated = True
        cur.execute(
            "SELECT * FROM students WHERE student_id = %s", (student_id,)
        )
        student = cur.fetchone()

    cur.close()
    db.close()
    return render_template("student/edit_profile.html", student=student, updated=updated)


@app.route("/student/reports")
def student_reports():
    if login_required_redirect():
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    student_id = session["student_id"]
    today = date.today().isoformat()

    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s", (student_id,)
    )
    total = cur.fetchone()["c"]
    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s AND status = 'Pending'",
        (student_id,),
    )
    pending = cur.fetchone()["c"]
    cur.execute(
        "SELECT COUNT(*) c FROM tasks WHERE student_id = %s AND status = 'Completed'",
        (student_id,),
    )
    completed = cur.fetchone()["c"]
    cur.execute(
        """SELECT COUNT(*) c FROM tasks
           WHERE student_id = %s AND due_date < %s AND status = 'Pending'""",
        (student_id, today),
    )
    overdue = cur.fetchone()["c"]
    cur.close()
    db.close()

    return render_template(
        "student/reports.html",
        total=total,
        pending=pending,
        completed=completed,
        overdue=overdue,
    )


# ---------------------------------------------------------------------------
# Init DB on startup so Gunicorn/Render picks it up
# ---------------------------------------------------------------------------
def ensure_database_ready():
    init_db()
    print("Database ready on Neon Postgres.")


ensure_database_ready()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

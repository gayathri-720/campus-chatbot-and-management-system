from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "campus.db"

# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
# ====== FOLDERS ======
UPLOAD_FOLDER = "uploads"
@app.route("/uploads/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
TIMETABLE_FOLDER = "timetables"
EXAM_TIMETABLE_FOLDER = "exam_timetables"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TIMETABLE_FOLDER, exist_ok=True)
os.makedirs(EXAM_TIMETABLE_FOLDER, exist_ok=True)


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = sqlite3.connect("campus.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cur.fetchone()
        conn.close()

        if user:

            session.clear()  # clear old session

            # ================= STUDENT LOGIN =================
            if user["role"] == "Student":

                # Allow only college email
                if not email.endswith("@klmcew.ac.in"):
                    return "Use your college email only!"

                # Extract roll number from email
                roll = email.split("@")[0].strip().upper()

                # Save roll in session
                session["roll"] = roll

            # ================= COMMON SESSION DATA =================
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            # ================= REDIRECT =================
            if user["role"] == "Student":
                return redirect("/student_dashboard")

            elif user["role"] == "Faculty":
                return redirect("/faculty_dashboard")

        else:
            return "Invalid Email or Password"

    return render_template("login.html")
# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        # ================= STUDENT EMAIL VALIDATION =================
        if role == "Student":

            # Format: 223h1a0501@klmcew.ac.in
            pattern = r"^\d{2}3h1a\d{4}@klmcew\.ac\.in$"

            if not re.match(pattern, email):
                error = "Use college mail only! Example: 223h1a0501@klmcew.ac.in"
                return render_template("register.html", error=error)

            # ⭐ EXTRACT ROLL NUMBER FROM EMAIL
            roll = email.split("@")[0].upper()

            # ⭐ DEFAULT CLASS DETAILS (change if needed)
            course = "B.Tech"
            year = "3"
            branch = "CSE"
            section = "A"

        # ============================================================

        conn = get_db()
        cur = conn.cursor()

        try:
            # ✅ Insert into users table
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, password, role)
            )

            # ✅ ALSO INSERT INTO students table (ONLY for students)
            if role == "Student":
                cur.execute("""
                    INSERT OR IGNORE INTO students
                    (roll, course, year, branch, section)
                    VALUES (?, ?, ?, ?, ?)
                """, (roll, course, year, branch, section))

            conn.commit()
            conn.close()

            return redirect("/")

        except sqlite3.IntegrityError:
            error = "Email already registered!"
            conn.close()

    return render_template("register.html", error=error)

# ================= STUDENT DASHBOARD =================
@app.route("/student_dashboard")
def student_dashboard():
    if "user_id" not in session:
        return redirect("/")

    roll = session.get("roll")  # ⭐ get roll

    return render_template("student_dashboard.html", roll=roll)

# ================= FACULTY DASHBOARD =================
@app.route("/faculty_dashboard")
def faculty_dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("faculty_dashboard.html")
# ---------------- ATTENDANCE MENU ----------------
@app.route("/attendance")
def attendance():
    if "user_id" not in session:
        return redirect("/")
    return render_template("attendance.html")



# ---------------- ADD STUDENT (ATTENDANCE) ----------------
@app.route("/add-student", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        start_roll = request.form.get("start_roll")
        end_roll = request.form.get("end_roll")

        course = request.form.get("course")
        year = request.form.get("year")
        branch = request.form.get("branch")
        section = request.form.get("section")

        exclude_input = request.form.get("exclude")

        # ---- Extract prefix and numbers ----
        prefix = start_roll[:-3]        # 22h1a
        start_num = int(start_roll[-3:])  # 501
        end_num = int(end_roll[-3:])      # 565

        # ---- Convert exclude list ----
        exclude_list = []
        if exclude_input:
            exclude_list = [int(x.strip()) for x in exclude_input.split(",")]

        conn = get_db()
        cursor = conn.cursor()

        for num in range(start_num, end_num + 1):

            if num not in exclude_list:

                roll = prefix + str(num).zfill(3)

                cursor.execute("""
                    INSERT OR IGNORE INTO students
                    (roll, course, year, branch, section)
                    VALUES (?, ?, ?, ?, ?)
                """, (roll, course, year, branch, section))

        conn.commit()
        conn.close()

        return redirect("/attendance")

    return render_template("add_student.html")

# ---------------- TAKE ATTENDANCE ----------------

from datetime import datetime

@app.route("/take-attendance", methods=["GET", "POST"])
def take_attendance():

    if request.method == "GET":
        return render_template("take_attendance.html")  # page with course/year/branch/section form

    # POST → after clicking submit
    course = request.form.get("course")
    year = request.form.get("year")
    branch = request.form.get("branch")
    section = request.form.get("section")

    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.roll,
               COALESCE(a.status, 'NOT MARKED') as status
        FROM students s
        LEFT JOIN attendance a
            ON s.roll = a.roll AND a.date = ?
        WHERE s.course=? AND s.year=? AND s.branch=? AND s.section=?
        ORDER BY s.roll
    """, (today, course, year, branch, section))

    students = cur.fetchall()
    conn.close()

    return render_template("attendance_table.html",
                           students=students,
                           course=course,
                           year=year,
                           branch=branch,
                           section=section)

@app.route("/save-attendance", methods=["POST"])
def save_attendance():

    if "user_id" not in session:
        return redirect("/")

    date = request.form.get("date")
    time = request.form.get("time")

    course = request.form.get("course")
    year = request.form.get("year")
    branch = request.form.get("branch")
    section = request.form.get("section")

    conn = get_db()
    cursor = conn.cursor()

    present_count = 0
    absent_count = 0

    for key in request.form:
        if key.startswith("status_"):

            roll = key.replace("status_", "").strip().upper()
            status = request.form.get(key)

            if status == "PRESENT":
                present_count += 1
            else:
                absent_count += 1

            cursor.execute("""
                INSERT INTO attendance (roll, date, time, status)
                VALUES (?, ?, ?, ?)
            """, (roll, date, time, status))

    conn.commit()

    # Reload same students list
    cursor.execute("""
        SELECT s.roll,
               IFNULL(
                 (SELECT status FROM attendance a
                  WHERE a.roll = s.roll
                  ORDER BY a.id DESC LIMIT 1),
               'ABSENT') AS status
        FROM students s
        WHERE s.course=? AND s.year=? AND s.branch=? AND s.section=?
        ORDER BY s.roll
    """, (course, year, branch, section))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "attendance_table.html",
        students=students,
        course=course,
        year=year,
        branch=branch,
        section=section,
        present_count=present_count,
        absent_count=absent_count
    )


from datetime import datetime
import sqlite3
from flask import request, render_template

def get_db():
    conn = sqlite3.connect("campus.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/monthly-attendance", methods=["GET", "POST"])
def monthly_attendance():

    # ✅ If opened directly → show form page
    if request.method == "GET":
        return render_template("monthly_attendance.html")

    # ✅ POST → generate report
    month = request.form.get("month")
    working_days = request.form.get("working_days")

    course = request.form.get("course")
    year = request.form.get("year")
    branch = request.form.get("branch")
    section = request.form.get("section")

    conn = sqlite3.connect("campus.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT s.roll,
               SUM(CASE WHEN a.status='PRESENT' THEN 1 ELSE 0 END) AS present_days,
               SUM(CASE WHEN a.status='ABSENT' THEN 1 ELSE 0 END) AS absent_days
        FROM students s
        LEFT JOIN attendance a
            ON s.roll = a.roll
            AND strftime('%m', a.date) = ?
        WHERE s.course=? AND s.year=? AND s.branch=? AND s.section=?
        GROUP BY s.roll
        ORDER BY s.roll
    """, (month, course, year, branch, section))

    rows = cur.fetchall()
    conn.close()

    attendance_data = []

    for r in rows:
        attendance_data.append({
            "roll": r["roll"],
            "present_days": r["present_days"] or 0,
            "absent_days": r["absent_days"] or 0
        })

    return render_template(
        "monthly_result.html",
        month=month,
        working_days=working_days,
        course=course,
        year=year,
        branch=branch,
        section=section,
        data=attendance_data
    )
# ================== STUDY MATERIAL ==================
@app.route("/study-material", methods=["GET", "POST"])
def study_material():

    if request.method == "POST":

        course = request.form.get("course")
        year = request.form.get("year")
        branch = request.form.get("branch")
        section = request.form.get("section")

        return redirect(f"/upload-material/{course}/{year}/{branch}/{section}")

    return render_template("select_material.html")
@app.route("/upload-material/<course>/<year>/<branch>/<section>", methods=["GET", "POST"])
def upload_material(course, year, branch, section):

    if "user_id" not in session:
        return redirect("/")

    folder = os.path.join(app.config["UPLOAD_FOLDER"], course, year, branch)
    os.makedirs(folder, exist_ok=True)

    if request.method == "POST":

        file = request.files.get("file")
        title = request.form.get("title")
        subject = request.form.get("subject")

        if file and file.filename:

            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))

            conn = get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO materials
                (title, subject, filename, course, year, branch, section, upload_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                subject,
                filename,
                course,
                year,
                branch,
                section,
                datetime.now().strftime("%Y-%m-%d")
            ))

            conn.commit()
            conn.close()

    files = os.listdir(folder)

    return render_template(
        "upload_material.html",
        course=course,
        year=year,
        branch=branch,
        section=section,
        files=files
    )
@app.route("/study-material-file/<course>/<year>/<branch>/<filename>")
def open_study_material(course, year, branch, filename):
    folder = os.path.join(app.config["UPLOAD_FOLDER"], course, year, branch)
    return send_from_directory(folder, filename)

# ================== FEES MODULE ==================
@app.route("/fees")
def fees_menu():
    if session.get("role") != "Faculty":
        return redirect("/")
    return render_template("fees_menu.html")


@app.route("/fees/add-student", methods=["GET", "POST"])
def fees_add_student():
    if session.get("role") != "Faculty":
        return redirect("/")

    if request.method == "POST":
        start_roll = request.form["start_roll"].upper()
        end_roll = request.form["end_roll"].upper()
        course = request.form["course"].strip()
        year = request.form["year"].strip()
        branch = request.form["branch"].upper()
        section = request.form["section"].upper()

        prefix = start_roll[:-2]
        start_num = int(start_roll[-2:])
        end_num = int(end_roll[-2:])

        conn = get_db()
        cur = conn.cursor()

        for i in range(start_num, end_num + 1):
            roll = prefix + f"{i:02d}"
            cur.execute("""
                INSERT OR IGNORE INTO students
                (roll, course, year, branch, section, fees_status)
                VALUES (?, ?, ?, ?, ?, 'NOT PAID')
            """, (roll, course, year, branch, section))

        conn.commit()
        conn.close()
        return redirect("/fees")

    return render_template("fees_add_student.html")


@app.route("/fees/check", methods=["GET", "POST"])
def fees_check_select():
    if session.get("role") != "Faculty":
        return redirect("/")

    if request.method == "POST":
        course = request.form["course"]
        year = request.form["year"]
        branch = request.form["branch"]
        section = request.form["section"]
        return redirect(f"/fees-details/{course}/{year}/{branch}/{section}")

    return render_template("fees_select.html")


@app.route("/fees-details/<course>/<year>/<branch>/<section>", methods=["GET", "POST"])
def fees_details(course, year, branch, section):
    if session.get("role") != "Faculty":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        roll = request.form["roll"]
        status = request.form["status"]
        cur.execute("UPDATE students SET fees_status=? WHERE roll=?", (status, roll))
        conn.commit()

    cur.execute("""
        SELECT roll, course, year, branch, fees_status
        FROM students
        WHERE course=? AND year=? AND branch=? AND section=?
        ORDER BY roll
    """, (course, year, branch, section))

    students = cur.fetchall()
    conn.close()

    return render_template("fees_check.html", students=students)
#-------------------TIME TABLE-------------

@app.route("/timetable")
def timetable():
    if "user_id" not in session or session["role"] != "Faculty":
        return redirect("/")
    return render_template("timetable.html")
# ---------------- CLASS TIME TABLE ----------------
@app.route("/class-timetable", methods=["GET", "POST"])
def class_timetable():
    if "user_id" not in session or session["role"] != "Faculty":
        return redirect("/")

    if request.method == "POST":
        course = request.form["course"]
        year = request.form["year"]
        branch = request.form["branch"]

        return redirect(f"/upload-timetable/{course}/{year}/{branch}")

    return render_template("select_timetable.html")

@app.route("/upload-timetable/<course>/<year>/<branch>", methods=["GET", "POST"])
def upload_timetable(course, year, branch):
    if "user_id" not in session or session["role"] != "Faculty":
        return redirect("/")

    folder = os.path.join(TIMETABLE_FOLDER, course, year, branch)
    os.makedirs(folder, exist_ok=True)

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))

    files = os.listdir(folder)

    return render_template("upload_timetable.html",
                           course=course,
                           year=year,
                           branch=branch,
                           files=files)

@app.route("/timetable-file/<course>/<year>/<branch>/<filename>")
def open_timetable(course, year, branch, filename):
    folder = os.path.join(TIMETABLE_FOLDER, course, year, branch)
    return send_from_directory(folder, filename)


# ---------------- EXAM TIME TABLE ----------------
@app.route("/exam-timetable", methods=["GET", "POST"])
def exam_timetable():
    if "user_id" not in session or session["role"] != "Faculty":
        return redirect("/")

    if request.method == "POST":
        course = request.form["course"]
        year = request.form["year"]
        branch = request.form["branch"]

        return redirect(f"/upload-exam-timetable/{course}/{year}/{branch}")

    return render_template("select_exam_timetable.html")

@app.route("/upload-exam-timetable/<course>/<year>/<branch>", methods=["GET", "POST"])
def upload_exam_timetable(course, year, branch):
    if "user_id" not in session or session["role"] != "Faculty":
        return redirect("/")

    folder = os.path.join(EXAM_TIMETABLE_FOLDER, course, year, branch)
    os.makedirs(folder, exist_ok=True)

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))

    files = os.listdir(folder)

    return render_template("upload_exam_timetable.html",
                           course=course,
                           year=year,
                           branch=branch,
                           files=files)
@app.route("/exam-timetable-file/<course>/<year>/<branch>/<filename>")
def open_exam_timetable(course, year, branch, filename):
    folder = os.path.join(EXAM_TIMETABLE_FOLDER, course, year, branch)
    return send_from_directory(folder, filename)

# ================= CREATE QUIZ PAGE =================
@app.route("/create_quiz", methods=["GET", "POST"])
def create_quiz():

    if request.method == "POST":
        course = request.form["course"]
        year = request.form["year"]
        branch = request.form["branch"]
        section = request.form["section"]

        return redirect(url_for(
            "upload_quiz",
            course=course,
            year=year,
            branch=branch,
            section=section
        ))

    return render_template("quiz_details.html")


# ================= UPLOAD QUIZ =================
@app.route("/upload_quiz/<course>/<year>/<branch>/<section>", methods=["GET", "POST"])
def upload_quiz(course, year, branch, section):

    if request.method == "POST":

        questions = request.form.getlist("question[]")
        option1_list = request.form.getlist("option1[]")
        option2_list = request.form.getlist("option2[]")
        option3_list = request.form.getlist("option3[]")
        option4_list = request.form.getlist("option4[]")
        correct_list = request.form.getlist("correct[]")

        conn = sqlite3.connect("campus.db")
        cur = conn.cursor()

        for i in range(len(questions)):
            cur.execute("""
                INSERT INTO quizzes
                (course, year, branch, section,
                 question, option1, option2, option3, option4, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                course, year, branch, section,
                questions[i],
                option1_list[i],
                option2_list[i],
                option3_list[i],
                option4_list[i],
                correct_list[i]
            ))

        conn.commit()
        conn.close()

        return redirect(url_for(
            "quiz_list",
            course=course,
            year=year,
            branch=branch,
            section=section
        ))

    # 👉 IMPORTANT — for GET request
    return render_template(
        "upload_quiz.html",
        course=course,
        year=year,
        branch=branch,
        section=section
    )
# ================= QUIZ LIST =================
@app.route("/quiz-list")
def quiz_list():

    course = request.args.get("course")
    year = request.args.get("year")
    branch = request.args.get("branch")
    section = request.args.get("section")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM quizzes
        WHERE course=? AND year=? AND branch=? AND section=?
        ORDER BY id DESC
    """, (course, year, branch, section))

    quizzes = cur.fetchall()
    conn.close()

    return render_template(
        "quiz_list.html",
        quizzes=quizzes,
        course=course,
        year=year,
        branch=branch,
        section=section
    )





# ================= VIEW ALL QUIZZES =================
@app.route("/view_quiz")
def view_quiz():

    conn = get_db()
    quizzes = conn.execute(
        "SELECT * FROM quizzes ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("view_quiz.html", quizzes=quizzes)


# ================= INTERNAL MARKS (FIXED) =================
# =========================================================

# STEP 1: Select details
@app.route("/select_internal_marks", methods=["GET", "POST"])
def select_internal_marks():
    if request.method == "POST":
        return redirect(url_for(
            "internal_marks_entry",
            course=request.form["course"],
            year=request.form["year"],
            branch=request.form["branch"],
            section=request.form["section"],
            mid=request.form["mid"]
        ))
    return render_template("select_internal_marks.html")

# STEP 2: Marks Entry Page
@app.route("/internal_marks_entry/<course>/<year>/<branch>/<section>/<mid>")
def internal_marks_entry(course, year, branch, section, mid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT roll FROM students
        WHERE course=? AND year=? AND branch=? AND section=?
        ORDER BY roll
    """, (course, year, branch, section))
    students = cur.fetchall()
    conn.close()

    return render_template(
        "internal_marks_entry.html",
        students=students,
        course=course,
        year=year,
        branch=branch,
        section=section,
        mid=mid
    )
# STEP 3: Save Marks
@app.route("/save_internal_marks", methods=["POST"])
def save_internal_marks():

    rolls = request.form.getlist("roll[]")
    bits = request.form.getlist("bit[]")
    assignments = request.form.getlist("assignment[]")
    theories = request.form.getlist("theory[]")
    totals = request.form.getlist("total[]")

    course = request.form["course"]
    year = request.form["year"]
    branch = request.form["branch"]
    section = request.form["section"]
    mid = request.form["mid"]

    conn = get_db()
    cur = conn.cursor()

    for i in range(len(rolls)):
        cur.execute("""
            INSERT INTO internal_marks
            (roll, course, year, branch, section, mid, bit, assignment, theory, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rolls[i], course, year, branch, section, mid,
            bits[i], assignments[i], theories[i], totals[i]
        ))

    conn.commit()
    conn.close()

    return redirect(url_for(
        "internal_marks_summary",
        course=course,
        year=year,
        branch=branch,
        section=section,
        mid=mid
    ))

# STEP 4: Summary + Print
@app.route("/internal_marks_summary")
def internal_marks_summary():

    course = request.args.get("course")
    year = request.args.get("year")
    branch = request.args.get("branch")
    section = request.args.get("section")
    mid = request.args.get("mid")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT roll, bit, assignment, theory, total
        FROM internal_marks
        WHERE course=? AND year=? AND branch=? AND section=? AND mid=?
        ORDER BY roll
    """, (course, year, branch, section, mid))

    data = cur.fetchall()
    conn.close()

    return render_template(
        "internal_marks_summary.html",
        data=data,
        count=len(data),
        course=course,
        year=year,
        branch=branch,
        section=section,
        mid=mid
    )
#------------------Student Details------------------
def get_student_details(roll):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT course, year, branch, section
        FROM students
        WHERE roll=?
    """, (roll,))

    data = cur.fetchone()
    conn.close()
    return data
@app.route("/student-attendance")
def student_attendance():

    if "roll" not in session:
        return redirect("/")

    roll = session["roll"].strip().upper()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, time, status
        FROM attendance
        WHERE UPPER(roll) = ?
        ORDER BY date DESC
    """, (roll,))

    records = cur.fetchall()
    conn.close()

    return render_template("student_attendance.html", records=records)
#-----------------------STUDENT STUDY MATERIAL VIEW-------------------
@app.route("/student-study-material")
def student_study_material():

    if "roll" not in session:
        return redirect("/")

    student = get_student_details(session["roll"])

    if not student:
        return "Student details not found"

    course, year, branch, section = student

    folder = os.path.join(
        app.config["UPLOAD_FOLDER"],
        course,
        year,
        branch
    )

    files = os.listdir(folder) if os.path.exists(folder) else []

    return render_template(
        "student_materials.html",
        files=files,
        course=course,
        year=year,
        branch=branch
    )
#-----------------------STUDENT TIMETABLE VIEW------------------------
@app.route("/student-timetable")
def student_timetable():

    if "roll" not in session:
        return redirect("/")

    student = get_student_details(session["roll"])

    course, year, branch, section = student

    folder = os.path.join(TIMETABLE_FOLDER, course, year, branch)
    files = os.listdir(folder) if os.path.exists(folder) else []

    return render_template(
        "student_timetable.html",
        files=files,
        course=course,
        year=year,
        branch=branch
    )
#------------------------------STUDENT EXAM TIMETABLE-----------------------
@app.route("/student-exam-timetable")
def student_exam_timetable():

    if "roll" not in session:
        return redirect("/")

    student = get_student_details(session["roll"])

    course, year, branch, section = student

    folder = os.path.join(EXAM_TIMETABLE_FOLDER, course, year, branch)
    files = os.listdir(folder) if os.path.exists(folder) else []

    return render_template(
        "student_exam_timetable.html",
        files=files,
        course=course,
        year=year,
        branch=branch
    )
#---------------------------------STUDENT QUIZ VIEW-----------------
@app.route("/student-quiz")
def student_quiz():

    if "roll" not in session:
        return redirect("/")

    student = get_student_details(session["roll"])

    course, year, branch, section = student

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM quizzes
        WHERE course=? AND year=? AND branch=? AND section=?
        ORDER BY id DESC
    """, (course, year, branch, section))

    quizzes = cur.fetchall()
    conn.close()

    return render_template("student_quiz.html", quizzes=quizzes)
#--------------------------------------STUDENT FEES STATUS---------------------
@app.route("/student_fees")
def student_fees():

    if "roll" not in session:
        return redirect("/student_login")

    roll = session["roll"].upper()

    conn = sqlite3.connect("campus.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT fees_status
        FROM students
        WHERE UPPER(roll) = ?
    """, (roll,))

    student = cur.fetchone()
    conn.close()

    if student:
        return render_template("student_fees.html", fees=student["fees_status"])
    else:
        return "Student not found"
#------------------------------STUDENT INTERNAL MARKS--------------------
@app.route("/api/student-attendance")
def api_student_attendance():

    if "roll" not in session:
        return {"attendance": []}
    roll = session["roll"].strip().upper()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, time, status
        FROM attendance
        WHERE UPPER(roll)=?
        ORDER BY date DESC
    """, (roll,))

    rows = cur.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "date": r["date"],
            "time": r["time"],
            "status": r["status"]
        })

    return {"attendance": data}
@app.route("/api/student-materials")
def api_student_materials():

    # 🔐 Check student login
    if "roll" not in session:
        return {"materials": []}

    roll = session["roll"].strip().upper()

    conn = get_db()
    cur = conn.cursor()

    # 🔹 Get student class details
    cur.execute("""
        SELECT course, year, branch, section
        FROM students
        WHERE roll=?
    """, (roll,))

    student = cur.fetchone()

    if not student:
        conn.close()
        return {"materials": []}

    course = student["course"]
    year = student["year"]
    branch = student["branch"]
    section = student["section"]

    # 🔹 Get materials for that class + section
    cur.execute("""
        SELECT title, subject, filename, upload_date
        FROM materials
        WHERE course=? AND year=? AND branch=?
        ORDER BY upload_date DESC
    """, (course, year, branch))

    rows = cur.fetchall()
    conn.close()

    materials = []

    for r in rows:
        materials.append({
            "title": r["title"],
            "subject": r["subject"],
            "filename": r["filename"],
            "date": r["upload_date"],
            "url": url_for(
                "open_study_material",
                course=course,
                year=year,
                branch=branch,
                filename=r["filename"]
            )
        })

    return {"materials": materials}
@app.route("/api/student-fees")
def student_fees_api():

    if "roll" not in session:
        return {"status": None}

    roll = session["roll"].upper()

    conn = sqlite3.connect("campus.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT fees_status
        FROM students
        WHERE UPPER(roll) = ?
    """, (roll,))

    student = cur.fetchone()
    conn.close()

    if student:
        return {"status": student["fees_status"]}
    else:
        return {"status": None}



@app.route("/api/student-timetable")
def student_timetable_api():

    if "roll" not in session:
        return {"files": []}

    roll = session["roll"].upper()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT course, year, branch
        FROM students
        WHERE UPPER(roll) = ?
    """, (roll,))

    student = cur.fetchone()
    conn.close()

    if not student:
        return {"files": []}

    course = student["course"]
    year = student["year"]
    branch = student["branch"]

    # ✅ Correct folder (same as upload)
    folder_path = os.path.join(
        TIMETABLE_FOLDER,
        course,
        year,
        branch
    )

    if not os.path.exists(folder_path):
        return {"files": []}

    files = os.listdir(folder_path)

    return {
        "files": files,
        "course": course,
        "year": year,
        "branch": branch
    }
@app.route("/api/student-quiz")
def student_quiz_api():

    if "roll" not in session:
        return {"quiz": []}

    roll = session["roll"].upper()

    conn = get_db()
    cur = conn.cursor()

    # Get student details
    cur.execute("""
        SELECT course, year, branch, section
        FROM students
        WHERE UPPER(roll) = ?
    """, (roll,))

    student = cur.fetchone()

    if not student:
        conn.close()
        return {"quiz": []}

    # 🔥 NORMALIZE YEAR (4th, 4th Year, 4 → 4)
    student_year = str(student["year"]).strip().lower()

    if "4" in student_year:
        student_year = "4"
    elif "3" in student_year:
        student_year = "3"
    elif "2" in student_year:
        student_year = "2"
    elif "1" in student_year:
        student_year = "1"

    # 🔥 Query quizzes ignoring year format differences
    cur.execute("""
        SELECT id, question, option1, option2, option3, option4
        FROM quizzes
        WHERE UPPER(course)=UPPER(?)
          AND branch=?
          AND section=?
    """, (
        student["course"],
        student["branch"],
        student["section"]
    ))

    rows = cur.fetchall()

    # 🔥 Filter in Python by year number
    filtered = []

    for r in rows:
        quiz_year = str(r["id"])  # Not needed if no year column selected

        filtered.append(dict(r))

    conn.close()

    return {"quiz": filtered}

@app.route("/api/student-internal")
def api_student_internal_marks():
    if "roll" not in session:
        return {"marks": []}

    roll = session["roll"].strip().upper()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT mid, bit, assignment, theory, total
        FROM internal_marks
        WHERE UPPER(roll)=?
        ORDER BY mid DESC
    """, (roll,))
    marks = cur.fetchall()
    conn.close()

    data = []
    for m in marks:
        data.append({
            "mid": m["mid"],
            "bit": m["bit"],
            "assignment": m["assignment"],
            "theory": m["theory"],
            "total": m["total"]
        })

    return {"marks": data}
# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

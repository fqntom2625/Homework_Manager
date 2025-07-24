from flask import Flask, render_template, request, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'students.db'

# -------------------------
# DB 초기화 함수
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 학생 테이블
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            day_group TEXT NOT NULL,
            level INTEGER NOT NULL
        )
    ''')

    # 학생별 수행 항목 테이블
    cur.execute('''
        CREATE TABLE IF NOT EXISTS student_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    # 날짜별 수행 상태 테이블
    cur.execute('''
        CREATE TABLE IF NOT EXISTS task_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('○', '△', '✕')),
            UNIQUE(student_id, date, task_name),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    conn.commit()
    conn.close()

# -------------------------
# 메인 페이지: 학생 목록
# -------------------------
@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY class_name, level, day_group, name")
    students = cur.fetchall()
    conn.close()
    return render_template('index.html', students=students)

# -------------------------
# 학생 추가
# -------------------------
@app.route('/add', methods=['POST'])
def add_student():
    name = request.form['name']
    class_name = request.form['class_name']
    day_group = request.form['day_group']
    level = int(request.form['level'])
    tasks = request.form.getlist('tasks')  # 체크된 항목

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO students (name, class_name, day_group, level) VALUES (?, ?, ?, ?)",
                (name, class_name, day_group, level))
    student_id = cur.lastrowid

    for task in tasks:
        cur.execute("INSERT INTO student_tasks (student_id, task_name) VALUES (?, ?)", (student_id, task))

    conn.commit()
    conn.close()
    return redirect('/')

# -------------------------
# 학생 삭제
# -------------------------
@app.route('/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
    cur.execute("DELETE FROM student_tasks WHERE student_id = ?", (student_id,))
    cur.execute("DELETE FROM task_records WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    return redirect('/')

# -------------------------
# 체크 페이지
# -------------------------
@app.route('/check', methods=['GET'])
def check_tasks():
    date = request.args.get('date') or datetime.today().strftime('%Y-%m-%d')
    class_name = request.args.get('class')
    day_group = request.args.get('day')
    level = request.args.get('level')

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM students
        WHERE class_name = ? AND day_group = ? AND level = ?
        ORDER BY name
    ''', (class_name, day_group, level))
    students = cur.fetchall()

    student_tasks = {}
    for student in students:
        sid = student[0]
        cur.execute("SELECT task_name FROM student_tasks WHERE student_id = ?", (sid,))
        tasks = [row[0] for row in cur.fetchall()]
        student_tasks[sid] = tasks

    conn.close()
    return render_template('check.html', students=students, student_tasks=student_tasks,
                           date=date, class_name=class_name, day_group=day_group, level=level)

# -------------------------
# 체크 결과 저장
# -------------------------
@app.route('/submit_check', methods=['POST'])
def submit_check():
    date = request.form['date']

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id FROM students")
    student_ids = [row[0] for row in cur.fetchall()]

    for sid in student_ids:
        cur.execute("SELECT task_name FROM student_tasks WHERE student_id = ?", (sid,))
        tasks = [row[0] for row in cur.fetchall()]

        for task in tasks:
            field_name = f"status_{sid}_{task}"
            status = request.form.get(field_name)
            if status in ['○', '△', '✕']:
                cur.execute('''
                    INSERT OR REPLACE INTO task_records (student_id, date, task_name, status)
                    VALUES (?, ?, ?, ?)
                ''', (sid, date, task, status))
            else:
                print(f"⚠️ 저장되지 않은 항목: student_id={sid}, task={task}, status={status}")

    conn.commit()
    conn.close()
    return redirect('/')

# -------------------------
# 앱 실행
# -------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)

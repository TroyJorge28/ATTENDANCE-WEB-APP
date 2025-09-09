from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import or_, text
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
db = SQLAlchemy(app)

# ======================
# Database Models
# ======================
class Student(db.Model):
    matricule = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    level = db.Column(db.Integer)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(50))
    role = db.Column(db.String(20))  # student or delegate

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_matricule = db.Column(db.String(20), db.ForeignKey('student.matricule'))
    course = db.Column(db.String(100))
    date_time = db.Column(db.DateTime)
    qr_status = db.Column(db.String(20))
    face_status = db.Column(db.String(20))
    final_status = db.Column(db.String(20))
    lecture_desc = db.Column(db.Text)

# ======================
# One-time lightweight migration helper (SQLite)
# ======================
def ensure_schema():
    with db.engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(attendance)"))}
        if 'qr_status' not in cols:
            conn.execute(text("ALTER TABLE attendance ADD COLUMN qr_status VARCHAR(20)"))
        if 'face_status' not in cols:
            conn.execute(text("ALTER TABLE attendance ADD COLUMN face_status VARCHAR(20)"))
        if 'final_status' not in cols:
            conn.execute(text("ALTER TABLE attendance ADD COLUMN final_status VARCHAR(20)"))
        if 'lecture_desc' not in cols:
            conn.execute(text("ALTER TABLE attendance ADD COLUMN lecture_desc TEXT"))

# ======================
# Admin Decorator
# ======================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

# Root redirect
@app.route('/')
def index():
    return redirect(url_for('admin_dashboard'))

# ======================
# Admin Dashboard
# ======================
@app.route('/admin')
@admin_required
def admin_dashboard():
    total_students = Student.query.count()
    total_attendance = Attendance.query.count()
    delegates = Student.query.filter_by(role='delegate').count()
    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_attendance=total_attendance,
                           delegates=delegates)

# ======================
# Manage Students
# ======================
@app.route('/admin/students')
@admin_required
def admin_students():
    q = request.args.get('q', '').strip()
    level = request.args.get('level', '').strip()
    query = Student.query
    if q:
        query = query.filter(or_(Student.name.contains(q), Student.matricule.contains(q)))
    if level:
        query = query.filter_by(level=int(level))
    students = query.all()
    return render_template('admin_students.html', students=students, q=q, level=level)

# ======================
# Add New Student
# ======================
@app.route('/admin/student/add', methods=['GET','POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        matricule = request.form['matricule'].strip()
        name = request.form['name'].strip()
        level = int(request.form['level'])
        email = request.form['email'].strip()
        phone = request.form['phone'].strip()
        specialty = request.form['specialty'].strip()
        role = request.form.get('role', 'student')

        if Student.query.get(matricule):
            flash(f"Student with matricule {matricule} already exists.", "danger")
            return redirect(url_for('add_student'))

        new_student = Student(
            matricule=matricule,
            name=name,
            level=level,
            email=email,
            phone=phone,
            specialty=specialty,
            role=role
        )
        db.session.add(new_student)
        db.session.commit()
        flash(f"Student {name} added successfully.", "success")
        return redirect(url_for('admin_students'))

    return render_template('add_student.html')

# ======================
# Edit Student
# ======================
@app.route('/admin/student/edit/<matricule>', methods=['GET','POST'])
@admin_required
def edit_student(matricule):
    student = Student.query.get_or_404(matricule)
    if request.method == 'POST':
        student.name = request.form['name'].strip()
        student.level = int(request.form['level'])
        student.email = request.form['email'].strip()
        student.phone = request.form['phone'].strip()
        student.specialty = request.form['specialty'].strip()
        db.session.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for('admin_students'))
    return render_template('edit_student.html', student=student)

# ======================
# Assign Delegate
# ======================
@app.route('/admin/student/assign_delegate/<matricule>', methods=['POST'])
@admin_required
def assign_delegate(matricule):
    student = Student.query.get_or_404(matricule)
    student.role = 'delegate'
    db.session.commit()
    flash(f"{student.name} is now a delegate.", "success")
    return redirect(url_for('admin_students'))

# ======================
# Delete Student (and their attendance)
# ======================
@app.route('/admin/student/delete/<matricule>', methods=['POST'])
@admin_required
def delete_student(matricule):
    student = Student.query.get_or_404(matricule)
    Attendance.query.filter_by(student_matricule=matricule).delete(synchronize_session=False)
    db.session.delete(student)
    db.session.commit()
    flash(f"Deleted student {student.name} and their attendance.", "success")
    return redirect(url_for('admin_students'))

# ======================
# Promote Students
# ======================
@app.route('/admin/students/promote', methods=['POST'])
@admin_required
def promote_students():
    students = Student.query.all()
    for s in students:
        if s.level < 4:
            s.level += 1
    db.session.commit()
    flash("All students promoted successfully.", "success")
    return redirect(url_for('admin_dashboard'))

# ======================
# Shared attendance queries
# ======================
def attendance_query_from_params():
    q = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    )
    matricule = request.args.get('matricule', '').strip()
    level = request.args.get('level', '').strip()
    course = request.args.get('course', '').strip()
    if matricule:
        q = q.filter(Attendance.student_matricule == matricule)
    if level:
        q = q.filter(Student.level == int(level))
    if course:
        q = q.filter(Attendance.course.contains(course))
    return q

# exports: if course provided, export all students for that course (ignore other filters)
def attendance_query_for_export():
    base = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    )
    course = request.args.get('course', '').strip()
    if course:
        return base.filter(Attendance.course == course)
    return attendance_query_from_params()

# ======================
# View Attendance
# ======================
@app.route('/admin/attendance')
@admin_required
def view_attendance():
    results = attendance_query_from_params().all()
    return render_template('admin_attendance.html', results=results)

# ======================
# Delete single attendance
# ======================
@app.route('/admin/attendance/delete/<int:attendance_id>', methods=['POST'])
@admin_required
def delete_attendance(attendance_id):
    att = Attendance.query.get_or_404(attendance_id)
    db.session.delete(att)
    db.session.commit()
    flash("Attendance record deleted.", "success")
    return redirect(url_for('view_attendance', **request.args))

# ======================
# Delete all attendance for a course
# ======================
@app.route('/admin/attendance/delete_by_course', methods=['POST'])
@admin_required
def delete_attendance_by_course():
    course = request.form.get('course', '').strip()
    if not course:
        flash("Course is required to delete by course.", "danger")
        return redirect(url_for('view_attendance'))
    deleted = Attendance.query.filter(Attendance.course == course).delete(synchronize_session=False)
    db.session.commit()
    flash(f"Deleted {deleted} attendance records for course {course}.", "success")
    return redirect(url_for('view_attendance', course=course))

# ======================
# Export Excel (course-wide when course is provided)
# ======================
@app.route('/admin/attendance/export_excel')
@admin_required
def export_excel():
    rows = attendance_query_for_export().all()
    data = [{
        "Matricule": att.student_matricule,
        "Name": stu.name or "",
        "Level": stu.level or "",
        "Course": att.course,
        "Date": att.date_time.strftime("%Y-%m-%d %H:%M") if att.date_time else "",
        "Status": att.final_status or "",
        "Lecture": att.lecture_desc or ""
    } for att, stu in rows]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="attendance.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================
# Export PDF (course-wide when course is provided)
# ======================
@app.route('/admin/attendance/export_pdf')
@admin_required
def export_pdf():
    rows = attendance_query_for_export().all()
    output = BytesIO()
    c = canvas.Canvas(output)
    y = 800
    for att, stu in rows:
        when = att.date_time.strftime("%Y-%m-%d %H:%M") if att.date_time else ""
        text = f"{when} - {att.course} - {stu.name or ''} - {att.final_status or ''}"
        c.drawString(50, y, text[:110])
        y -= 20
        if y < 50:
            c.showPage()
            y = 800
    c.save()
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="attendance.pdf",
        mimetype="application/pdf"
    )

# ======================
# Run App
# ======================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_schema()
    app.run(debug=True)
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from database_models.models import Student, Attendance, promote_students, User
from database_models.extensions import db
from sqlalchemy import or_, text
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from functools import wraps
import os
from werkzeug.utils import secure_filename

# Use a unique blueprint name to avoid conflicts
admin = Blueprint('admin_panel', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return decorated


@admin.route('/')
@login_required
@admin_required
def admin_dashboard():
    total_students = Student.query.count()
    total_attendance = Attendance.query.count()
    delegates = Student.query.filter_by(role='delegate').count()
    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_attendance=total_attendance,
                           delegates=delegates)


@admin.route('/profile', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_profile():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Check if username is already taken by another user
        if username != current_user.username and User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('admin_panel.admin_profile'))

        # Update username
        current_user.username = username

        # Update email
        current_user.student.email = email

        # Update password if provided
        if new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('admin_panel.admin_profile'))
            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return redirect(url_for('admin_panel.admin_profile'))
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('admin_panel.admin_dashboard'))

    return render_template('admin_profile.html')


@admin.route('/students')
@login_required
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


@admin.route('/student/add', methods=['GET', 'POST'])
@login_required
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

        # Handle picture upload
        picture = request.files['picture']
        picture_path = None
        if picture and picture.filename != '':
            filename = secure_filename(picture.filename)
            picture_path = os.path.join('uploads', filename)
            picture.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        if Student.query.get(matricule):
            flash(f"Student with matricule {matricule} already exists.", "danger")
            return redirect(url_for('admin_panel.add_student'))

        new_student = Student(
            matricule=matricule, name=name, level=level, email=email,
            phone=phone, specialty=specialty, role=role, picture=picture_path
        )
        db.session.add(new_student)
        db.session.commit()
        flash(f"Student {name} added successfully.", "success")
        return redirect(url_for('admin_panel.admin_students'))

    return render_template('add_student.html')


@admin.route('/student/edit/<matricule>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(matricule):
    student = Student.query.get_or_404(matricule)
    if request.method == 'POST':
        student.name = request.form['name'].strip()
        student.level = int(request.form['level'])
        student.email = request.form['email'].strip()
        student.phone = request.form['phone'].strip()
        student.specialty = request.form['specialty'].strip()
        student.role = request.form['role']

        # Handle picture upload
        picture = request.files['picture']
        if picture and picture.filename != '':
            filename = secure_filename(picture.filename)
            picture_path = os.path.join('uploads', filename)
            picture.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            student.picture = picture_path

        # Update user role if exists
        user = User.query.filter_by(matricule=matricule).first()
        if user:
            user.role = student.role

        db.session.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for('admin_panel.admin_students'))

    return render_template('edit_student.html', student=student)


@admin.route('/student/assign_delegate/<matricule>', methods=['POST'])
@login_required
@admin_required
def assign_delegate(matricule):
    student = Student.query.get_or_404(matricule)
    student.role = 'delegate'

    # Update user role if exists
    user = User.query.filter_by(matricule=matricule).first()
    if user:
        user.role = 'delegate'

    db.session.commit()
    flash(f"{student.name} is now a delegate.", "success")
    return redirect(url_for('admin_panel.admin_students'))


@admin.route('/student/delete/<matricule>', methods=['POST'])
@login_required
@admin_required
def delete_student(matricule):
    student = Student.query.get_or_404(matricule)
    Attendance.query.filter_by(student_matricule=matricule).delete(synchronize_session=False)
    db.session.delete(student)
    db.session.commit()
    flash(f"Deleted student {student.name} and their attendance.", "success")
    return redirect(url_for('admin_panel.admin_students'))


@admin.route('/students/promote', methods=['POST'])
@login_required
@admin_required
def promote_students_route():
    promote_students()
    flash("All students promoted successfully.", "success")
    return redirect(url_for('admin_panel.admin_dashboard'))


@admin.route('/attendance')
@login_required
@admin_required
def view_attendance():
    # Get filter parameters
    matricule_filter = request.args.get('matricule', '').strip()
    level_filter = request.args.get('level', '').strip()
    course_filter = request.args.get('course', '').strip()

    # Build query
    query = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    )

    # Apply filters
    if matricule_filter:
        query = query.filter(Student.matricule.contains(matricule_filter))
    if level_filter:
        query = query.filter(Student.level == int(level_filter))
    if course_filter:
        query = query.filter(Attendance.course.contains(course_filter))

    results = query.all()

    return render_template('admin_attendance.html', results=results)


@admin.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
@login_required
@admin_required
def delete_attendance(attendance_id):
    att = Attendance.query.get_or_404(attendance_id)
    db.session.delete(att)
    db.session.commit()
    flash("Attendance record deleted.", "success")
    return redirect(url_for('admin_panel.view_attendance'))


# NEW ROUTE FOR DELETING MULTIPLE ATTENDANCE RECORDS
@admin.route('/attendance/delete_selected', methods=['POST'])
@login_required
@admin_required
def delete_selected_attendance():
    attendance_ids = request.form.getlist('attendance_ids')
    redirect_url = request.form.get('redirect_url', url_for('admin_panel.view_attendance'))

    if not attendance_ids:
        flash('No attendance records selected for deletion.', 'warning')
        return redirect(redirect_url)

    # Convert string IDs to integers
    try:
        attendance_ids = [int(id) for id in attendance_ids]
    except ValueError:
        flash('Invalid attendance IDs provided.', 'danger')
        return redirect(redirect_url)

    # Delete selected records
    deleted_count = Attendance.query.filter(Attendance.id.in_(attendance_ids)).delete(synchronize_session=False)
    db.session.commit()

    flash(f'Successfully deleted {deleted_count} attendance record(s).', 'success')
    return redirect(redirect_url)


@admin.route('/attendance/export_excel')
@login_required
@admin_required
def export_excel():
    results = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    ).all()

    data = [{
        "Matricule": att.student_matricule,
        "Name": stu.name or "",
        "Level": stu.level or "",
        "Course": att.course,
        "Date": att.date_time.strftime("%Y-%m-%d %H:%M") if att.date_time else "",
        "Status": att.final_status or "",
        "Lecture": att.lecture_description or ""
    } for att, stu in results]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    output.seek(0)
    return send_file(
        output, as_attachment=True, download_name="attendance.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@admin.route('/attendance/export_pdf')
@login_required
@admin_required
def export_pdf():
    results = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    ).all()

    output = BytesIO()
    c = canvas.Canvas(output)
    y = 800

    for att, stu in results:
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
        output, as_attachment=True, download_name="attendance.pdf",
        mimetype="application/pdf"
    )
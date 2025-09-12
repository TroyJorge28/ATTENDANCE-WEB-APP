from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify, \
    send_file
from flask_login import login_required, current_user
from database_models.models import Student, Attendance
from database_models.extensions import db
from datetime import datetime, timedelta
import qrcode
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mock_cv2 as cv2
import mock_face_recognition as face_recognition
from werkzeug.utils import secure_filename
import io
import base64
import time
import numpy as np
from PIL import Image

delegate = Blueprint('delegate', __name__, url_prefix='/delegate')


@delegate.route('/dashboard')
@login_required
def delegate_dashboard():
    if current_user.role != 'delegate':
        flash('Delegate access required', 'danger')
        return redirect(url_for('main.dashboard'))

    delegate_student = Student.query.get(current_user.matricule)
    students = Student.query.filter_by(level=delegate_student.level).all()

    # Get current session info
    current_session = session.get('current_session')

    # Get attendance records for this delegate's level
    attendance_records = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    ).filter(Student.level == delegate_student.level).all()

    return render_template('delegate_dashboard.html',
                           user_name=delegate_student.name,
                           user_matricule=delegate_student.matricule,
                           students=students,
                           current_session=current_session,
                           attendance_records=attendance_records,
                           datetime=datetime)


@delegate.route('/start_session', methods=['POST'])
@login_required
def start_session():
    if current_user.role != 'delegate':
        flash('Delegate access required', 'danger')
        return redirect(url_for('main.dashboard'))

    course = request.form['course']
    date = request.form['date']
    time = request.form['time']
    lecture_description = request.form.get('lecture_description', '')

    # Get delegate's level
    delegate_student = Student.query.get(current_user.matricule)
    level = delegate_student.level

    # Get all students in the delegate's level (excluding the delegate)
    students = Student.query.filter_by(level=level).filter(Student.matricule != current_user.matricule).all()

    # Create session with list of students
    session['current_session'] = {
        'course': course,
        'date': date,
        'time': time,
        'lecture_description': lecture_description,
        'students': [],
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'qr_expiry': (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
        'level': level
    }

    # Auto-mark delegate as present (as per requirement)
    # Check if delegate already has an attendance record for this session
    existing_delegate_attendance = Attendance.query.filter_by(
        student_matricule=delegate_student.matricule,
        course=course,
        date_time=datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    ).first()

    if not existing_delegate_attendance:
        attendance = Attendance(
            student_matricule=delegate_student.matricule,
            course=course,
            date_time=datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"),
            qr_scan_status=True,
            face_id_status=True,
            final_status='present',
            lecture_description=lecture_description
        )
        db.session.add(attendance)
        db.session.commit()

    # Generate QR codes for all students in the level (excluding the delegate)
    for student in students:
        # Create QR code data with student info and timestamp
        qr_data = f"{student.matricule}-{course}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate QR code
        qr_img = qrcode.make(qr_data)

        # Convert to base64 for display
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

        # Add to session
        session['current_session']['students'].append({
            'matricule': student.matricule,
            'name': student.name,
            'qr_scanned': False,
            'face_verified': False,
            'qr_code': qr_base64
        })

    # Update session
    session.modified = True

    # Send notification to students
    # In a real application, this would send emails or push notifications
    flash('Session started and QR codes generated for all students', 'success')
    return redirect(url_for('delegate.delegate_dashboard'))


@delegate.route('/end_session', methods=['POST'])
@login_required
def end_session():
    if current_user.role != 'delegate':
        flash('Delegate access required', 'danger')
        return redirect(url_for('main.dashboard'))

    current_session = session.get('current_session')
    if current_session:
        # Get delegate's matricule to exclude them from being marked absent
        delegate_matricule = current_user.matricule

        # Mark all students who haven't completed both QR and Face ID as absent
        for student_data in current_session['students']:
            # Skip the delegate
            if student_data['matricule'] == delegate_matricule:
                continue

            # Check if student already has an attendance record for this session
            session_datetime = datetime.strptime(f"{current_session['date']} {current_session['time']}",
                                                 "%Y-%m-%d %H:%M")
            existing_attendance = Attendance.query.filter_by(
                student_matricule=student_data['matricule'],
                course=current_session['course'],
                date_time=session_datetime
            ).first()

            # Only create a new record if one doesn't exist
            if not existing_attendance and (
                    not student_data.get('qr_scanned') or not student_data.get('face_verified')):
                # Create attendance record as absent
                attendance = Attendance(
                    student_matricule=student_data['matricule'],
                    course=current_session['course'],
                    date_time=session_datetime,
                    qr_scan_status=student_data.get('qr_scanned', False),
                    face_id_status=student_data.get('face_verified', False),
                    final_status='absent',
                    lecture_description=current_session.get('lecture_description', '')
                )
                db.session.add(attendance)

        db.session.commit()
        session.pop('current_session', None)
        flash('Session ended and attendance recorded', 'success')

    return redirect(url_for('delegate.delegate_dashboard'))


# Comment out the face verification function for now
# @delegate.route('/verify_face/<student_matricule>', methods=['GET'])
# @login_required
# def verify_face(student_matricule):
#     # ... function code ...

@delegate.route('/export_attendance')
@login_required
def export_attendance():
    if current_user.role != 'delegate':
        flash('Delegate access required', 'danger')
        return redirect(url_for('main.dashboard'))

    delegate_student = Student.query.get(current_user.matricule)

    # Get attendance records for this delegate's level
    attendance_records = db.session.query(Attendance, Student).join(
        Student, Attendance.student_matricule == Student.matricule
    ).filter(Student.level == delegate_student.level).all()

    format = request.args.get('format', 'excel')

    if format == 'excel':
        # Export to Excel
        from openpyxl import Workbook
        from io import BytesIO

        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Records"

        # Add headers
        ws.append(["Matricule", "Name", "Course", "Date", "Status", "Lecture Description"])

        # Add data
        for att, stu in attendance_records:
            ws.append([
                att.student_matricule,
                stu.name,
                att.course,
                att.date_time.strftime("%Y-%m-%d %H:%M") if att.date_time else "",
                att.final_status,
                att.lecture_description or ""
            ])

        # Save to a BytesIO object
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"attendance_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif format == 'pdf':
        # Export to PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.lib import colors
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Prepare data
        data = [["Matricule", "Name", "Course", "Date", "Status", "Lecture Description"]]

        for att, stu in attendance_records:
            data.append([
                att.student_matricule,
                stu.name,
                att.course,
                att.date_time.strftime("%Y-%m-%d %H:%M") if att.date_time else "",
                att.final_status,
                att.lecture_description or ""
            ])

        # Create table
        table = Table(data)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        # Build PDF
        doc.build([table])
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"attendance_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype="application/pdf"
        )

    else:
        flash('Invalid export format', 'danger')
        return redirect(url_for('delegate.delegate_dashboard'))
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
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

student = Blueprint('student', __name__, url_prefix='/student')


@student.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Student access required', 'danger')
        return redirect(url_for('main.dashboard'))

    student_data = Student.query.get(current_user.matricule)
    attendance_records = Attendance.query.filter_by(student_matricule=current_user.matricule).all()

    # Get notifications
    notifications = session.get('notifications', [])

    # Get current session info if available
    current_session = session.get('current_session')

    # Get current date for the form
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Pass both datetime module and current_date to template
    return render_template('student_dashboard.html',
                           user_name=student_data.name,
                           user_matricule=student_data.matricule,
                           attendance_records=attendance_records,
                           notifications=notifications,
                           current_session=current_session,
                           datetime=datetime,
                           current_date=current_date)


@student.route('/scan_qr', methods=['POST'])
@login_required
def scan_qr():
    if current_user.role != 'student':
        return jsonify({'success': False, 'message': 'Student access required'})

    data = request.get_json()
    qr_data = data.get('qr_data')

    if not qr_data:
        return jsonify({'success': False, 'message': 'No QR data provided'})

    # Get the current session
    current_session = session.get('current_session')
    if not current_session:
        return jsonify({'success': False, 'message': 'No active session'})

    # Check if the student is in the same level as the session
    student_data = Student.query.get(current_user.matricule)
    if student_data.level != current_session.get('level'):
        return jsonify({'success': False, 'message': 'This session is not for your level'})

    # Check if QR is still valid (30 minutes from session start)
    session_start = datetime.strptime(current_session['start_time'], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > session_start + timedelta(minutes=30):
        return jsonify({'success': False, 'message': 'QR code scanning period has expired'})

    # Check if student has already scanned QR
    for s in current_session.get('students', []):
        if s['matricule'] == current_user.matricule and s.get('qr_scanned'):
            return jsonify({'success': False, 'message': 'You have already scanned your QR code'})

    # Update the student's QR scan status in the session
    for student in current_session.get('students', []):
        if student['matricule'] == current_user.matricule:
            student['qr_scanned'] = True
            student['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break

    session.modified = True

    return jsonify({'success': True, 'message': 'QR code scanned successfully'})


# Comment out the face verification function for now
# @student.route('/verify_face', methods=['POST'])
# @login_required
# def verify_face():
#     # ... function code ...

@student.route('/clear_notifications')
@login_required
def clear_notifications():
    if current_user.role != 'student':
        flash('Student access required', 'danger')
        return redirect(url_for('main.dashboard'))

    session['notifications'] = []
    flash('Notifications cleared', 'success')
    return redirect(url_for('student.student_dashboard'))
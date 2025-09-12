from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database_models.models import User, Student
from database_models.extensions import db
import random
import string

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        # Check if user exists and password is correct
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))

        # If user is delegate, check if they have a valid session
        if user.role == 'delegate':
            current_session = session.get('current_session')
            if current_session:
                flash('You have an active session. Please end it before logging in again.', 'warning')
                return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        matricule = request.form.get('matricule')
        name = request.form.get('name')
        level = int(request.form.get('level'))
        password = request.form.get('password')

        # Check if student already exists
        student = Student.query.get(matricule)
        if student:
            flash('Matricule already exists', 'danger')
            return redirect(url_for('auth.signup'))

        # Create new student
        new_student = Student(
            matricule=matricule,
            name=name,
            level=level
        )
        db.session.add(new_student)
        db.session.commit()

        # Create user account
        new_user = User(
            username=matricule,  # Use matricule as username
            matricule=matricule,
            role='student'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth.route('/logout')
@login_required
def logout():
    # If user is delegate, end any active session
    if current_user.role == 'delegate':
        current_session = session.get('current_session')
        if current_session:
            # Mark all students who haven't completed both QR and Face ID as absent
            for student_data in current_session['students']:
                if not student_data.get('qr_scanned') or not student_data.get('face_verified'):
                    # Create attendance record as absent
                    from database_models.models import Attendance
                    from datetime import datetime
                    attendance = Attendance(
                        student_matricule=student_data['matricule'],
                        course=current_session['course'],
                        date_time=datetime.strptime(f"{current_session['date']} {current_session['time']}",
                                                    "%Y-%m-%d %H:%M"),
                        qr_scan_status=student_data.get('qr_scanned', False),
                        face_id_status=student_data.get('face_verified', False),
                        final_status='absent',
                        lecture_description=current_session.get('lecture_description', '')
                    )
                    db.session.add(attendance)
            db.session.commit()
            session.pop('current_session', None)

    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')

        # Find student by email
        student = Student.query.filter_by(email=email).first()
        if not student:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('auth.reset_request'))

        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))

        # Store OTP in session (in a real app, you would email it)
        session['reset_otp'] = otp
        session['reset_email'] = email

        flash(f'OTP has been sent to {email}. (For demo: OTP is {otp})', 'info')
        return redirect(url_for('auth.reset_password', email=email))

    return render_template('reset_request.html')


@auth.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        otp = request.form.get('otp')
        password = request.form.get('password')

        # Verify OTP
        if otp != session.get('reset_otp'):
            flash('Invalid OTP. Please try again.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

        # Find student by email
        student = Student.query.filter_by(email=email).first()
        if not student:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('auth.reset_request'))

        # Update password
        user = User.query.filter_by(matricule=student.matricule).first()
        if user:
            user.set_password(password)
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('reset_password.html', email=email)


@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.change_password'))

        # Verify new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('auth.change_password'))

        # Update password
        current_user.set_password(new_password)
        db.session.commit()

        flash('Password updated successfully', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('change_password.html')


@auth.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'POST':
        new_username = request.form.get('new_username')
        password = request.form.get('password')

        # Verify password
        if not current_user.check_password(password):
            flash('Password is incorrect', 'danger')
            return redirect(url_for('auth.change_username'))

        # Check if username is already taken
        if User.query.filter_by(username=new_username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('auth.change_username'))

        # Update username
        current_user.username = new_username
        db.session.commit()

        flash('Username updated successfully', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('change_username.html')
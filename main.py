from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_panel.admin_dashboard'))
    elif current_user.role == 'delegate':
        return redirect(url_for('delegate.delegate_dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('student.student_dashboard'))
    else:
        return redirect(url_for('auth.login'))
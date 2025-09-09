from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dashboards-only-secret-12345'

# Mock data storage (your teammate will replace this with actual database)
users = []
attendance_records = []
current_session = None


# Temporary route for testing
@app.route('/')
def home():
    return '''
    <h1>Attendance System Dashboards</h1>
    <p><a href="/student/dashboard">Student Dashboard</a></p>
    <p><a href="/delegate/dashboard">Delegate Dashboard</a></p>
    <p><em>Note: Your teammate will implement proper authentication</em></p>
    '''


# Dashboard Routes - No authentication checks (handled by your teammate)
@app.route('/student/dashboard')
def student_dashboard():
    # Your teammate will handle authentication and set session variables
    student_name = session.get('user_name', 'Test Student')
    student_matricule = session.get('user_matricule', 'STU001')

    # Filter attendance records for this student
    student_attendance = [r for r in attendance_records if r.get('matricule') == student_matricule]

    return render_template('student_dashboard.html',
                           user_name=student_name,
                           user_matricule=student_matricule,
                           attendance_records=student_attendance)  # Fixed typo


@app.route('/delegate/dashboard')
def delegate_dashboard():
    # Your teammate will handle authentication and set session variables
    delegate_name = session.get('user_name', 'Test Delegate')
    delegate_matricule = session.get('user_matricule', 'DEL001')

    # Get all students for the delegate to manage
    all_students = [u for u in users if u.get('role') == 'student']

    return render_template('delegate_dashboard.html',
                           user_name=delegate_name,
                           user_matricule=delegate_matricule,
                           students=all_students,
                           current_session=current_session,
                           datetime=datetime)


# ... (keep the rest of your delegate functions as they were)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
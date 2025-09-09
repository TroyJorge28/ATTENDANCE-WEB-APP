from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ----------------- MODELS -----------------
class Student(db.Model):
    matricule = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), db.ForeignKey('student.matricule'))
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- ROUTES -----------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        matricule = request.form['matricule'].strip()
        name = request.form['name'].strip()
        level_raw = request.form['level'].strip()
        password = request.form['password']

        try:
            level = int(level_raw)
        except ValueError:
            flash("Level must be a number", "danger")
            return render_template('signup.html')

        student = Student.query.filter_by(matricule=matricule, name=name, level=level).first()
        if student:
            if User.query.filter_by(username=matricule).first():
                flash("User already exists", "warning")
                return redirect(url_for('login'))
            hashed_password = generate_password_hash(password)
            user = User(matricule=matricule, username=matricule, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for('login'))
        else:
            flash("Student record not found or details do not match", "danger")
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome! You are logged in as {current_user.username}."

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['email'].strip()
        student = Student.query.filter_by(email=email).first()
        if student:
            otp = str(random.randint(100000, 999999))
            print(f"OTP for {email}: {otp}")
            flash("OTP sent! (Check terminal for now)", "info")
            return redirect(url_for('reset_password', email=email))
        else:
            flash("Email not found", "danger")
    return render_template('reset_request.html')

@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        otp = request.form['otp']
        password = request.form['password']
        student = Student.query.filter_by(email=email).first()
        if not student:
            flash("Email not found", "danger")
            return redirect(url_for('reset_request'))
        user = User.query.filter_by(matricule=student.matricule).first()
        if user:
            user.password = generate_password_hash(password)
            db.session.commit()
            flash("Password reset successfully!", "success")
            return redirect(url_for('login'))
        else:
            flash("User not found", "danger")
    return render_template('reset_password.html', email=email)

# ----------------- RUN APP -----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
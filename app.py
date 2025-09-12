import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, redirect, url_for
from flask_login import current_user
from database_models.models import User, Student, Attendance
from database_models.config import Config
from database_models.extensions import db, migrate, login_manager
from auth_security.auth import auth as auth_blueprint
from admin_panel.admin import admin as admin_blueprint
from dashboards.delegate import delegate as delegate_blueprint
from dashboards.student import student as student_blueprint
from qr_face.qr_face import qr_face as qr_face_blueprint
from main import main as main_blueprint
from werkzeug.security import generate_password_hash
import os

app = Flask(__name__)
app.config.from_object(Config)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

# Register blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(admin_blueprint)
app.register_blueprint(delegate_blueprint)
app.register_blueprint(student_blueprint)
app.register_blueprint(qr_face_blueprint)
app.register_blueprint(main_blueprint)

# Create tables and default admin user
with app.app_context():
    db.create_all()

    # Check if admin user exists, if not create one
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        # Create a student record for the admin first
        admin_student = Student(
            matricule='ADMIN001',
            name='System Administrator',
            level=1,
            email='admin@example.com',
            role='admin'
        )
        db.session.add(admin_student)
        db.session.commit()

        # Create the admin user account
        admin_user = User(
            username='admin',
            matricule='ADMIN001',
            role='admin'
        )
        admin_user.set_password('admin123')  # Default password
        db.session.add(admin_user)
        db.session.commit()
        print("🔑 Default admin user created: username=admin, password=admin123")

    print("📦 Database & tables created successfully!")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


#if __name__ == '__main__':

#    app.run(debug=True)

if __name__ == '__main__':
        app.run()

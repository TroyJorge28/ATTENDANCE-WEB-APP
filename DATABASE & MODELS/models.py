from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------------
# STUDENT MODEL
# -------------------------
class Student(db.Model):
    __tablename__ = 'students'
    matricule = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(50))
    role = db.Column(db.Enum('student', 'delegate', name='role_enum'), default='student')
    picture = db.Column(db.String(255))

    # Relationships
    attendances = db.relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
        single_parent=True
    )
    user = db.relationship(
        "User",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True
    )

    def __repr__(self):
        return f"<Student {self.matricule} - {self.name} (Level {self.level})>"


# -------------------------
# USER MODEL
# -------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('student', 'delegate', 'admin', name='user_role_enum'), nullable=False)
    matricule = db.Column(db.String(20), db.ForeignKey('students.matricule'))

    # Relationship
    student = db.relationship("Student", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# -------------------------
# ATTENDANCE MODEL
# -------------------------
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_matricule = db.Column(db.String(20), db.ForeignKey('students.matricule'))
    course = db.Column(db.String(100), nullable=False)
    date_time = db.Column(db.DateTime, default=datetime.utcnow)
    qr_scan_status = db.Column(db.Boolean, default=False)
    face_id_status = db.Column(db.Boolean, default=False)
    final_status = db.Column(db.Enum('present', 'absent', name='status_enum'), default='absent')
    lecture_description = db.Column(db.Text)

    # Relationship
    student = db.relationship("Student", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance {self.student_matricule} - {self.course} - {self.final_status}>"

# -------------------------
# HELPER FUNCTION
# -------------------------
def promote_students():
    """Promotes students to the next level at the start of a new academic year."""
    students = Student.query.all()
    for student in students:
        if student.level < 4:  # Promote up to level 4 only
            student.level += 1
    db.session.commit()
    print("✅ All students promoted to next level (where applicable).")
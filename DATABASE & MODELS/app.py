from flask import Flask, jsonify
from config import Config
from models import db, Student, User, Attendance, promote_students

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Create tables once
with app.app_context():
    db.create_all()
    print("📦 Database & tables created successfully!")


# -------------------------
# DELETE ENDPOINTS
# -------------------------
@app.delete('/students/<string:matricule>')
def delete_student(matricule):
    student = Student.query.get(matricule)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "Student deleted", "matricule": matricule}), 200


@app.delete('/users/<int:user_id>')
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted", "id": user_id}), 200


@app.delete('/attendance/<int:attendance_id>')
def delete_attendance(attendance_id):
    record = Attendance.query.get(attendance_id)
    if not record:
        return jsonify({"error": "Attendance not found"}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Attendance deleted", "id": attendance_id}), 200

if __name__ == "__main__":
    app.run(debug=True)
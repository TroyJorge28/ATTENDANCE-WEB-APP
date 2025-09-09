from flask import Flask, jsonify, send_file
import qrcode
import cv2
import face_recognition
import os
import csv
from datetime import datetime, date

app = Flask(__name__)

# ------------------------
# Student "DB" (simulate database)
# ------------------------
students = {
    "S001": {"name": "Delegate", "picture_path": "delegate.jpg", "role": "Delegate"},
    "S002": {"name": "Bob", "picture_path": "bob.jpg", "role": "Student"},
    "S003": {"name": "Charlie", "picture_path": "charlie.jpg", "role": "Student"},
    "S004": {"name": "Alice", "picture_path": "alice.jpg", "role": "Student"}
}

# ------------------------
# Folders and attendance file
# ------------------------
QR_FOLDER = "qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

ATTENDANCE_FILE = "attendance.csv"

# Create attendance file if it doesn’t exist
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "name", "status", "timestamp"])

# Store scan order (list of student_ids)
scan_order = []


# ------------------------
# 1. Generate QR codes (Delegate action)
# ------------------------
@app.route("/generate_qr", methods=["POST"])
def generate_qr_for_all():
    global scan_order
    scan_order = []

    # Clear previous QR images
    for file in os.listdir(QR_FOLDER):
        os.remove(os.path.join(QR_FOLDER, file))

    qr_list = []

    for sid, data in students.items():
        # Only students (exclude delegate) for QR generation
        if data["role"] != "Student":
            continue

        qr_data = f"{sid}-QR"
        filename = os.path.join(QR_FOLDER, f"{sid}.png")
        img = qrcode.make(qr_data)
        img.save(filename)
        qr_list.append({"student_id": sid, "name": data["name"], "qr_file": filename})
        scan_order.append({"student_id": sid, "name": data["name"]})

    # Auto-mark delegate as present
    delegate_id = None
    for sid, data in students.items():
        if data["role"] == "Delegate":
            delegate_id = sid
            with open(ATTENDANCE_FILE, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([sid, data["name"], "Present", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            break

    return jsonify({
        "message": "QR codes generated",
        "qr_list": qr_list,
        "delegate_marked_present": delegate_id,
        "scan_order": scan_order
    })


# ------------------------
# 2. Get scan order (student order list)
# ------------------------
@app.route("/get_scan_order", methods=["GET"])
def get_scan_order():
    return jsonify(scan_order)


# ------------------------
# 3. Face ID Verification + Mark Present
# ------------------------
@app.route("/verify_face/<student_id>", methods=["GET"])
def verify_face(student_id):
    if student_id not in students or students[student_id]["role"] != "Student":
        return jsonify({"error": "Student not found"}), 404

    student = students[student_id]
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return jsonify({"error": "Camera not available"}), 500

    result = {"student": student["name"], "status": "Face Not Recognised"}
    match = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        face_locations = face_recognition.face_locations(frame)
        if face_locations:
            captured_encoding = face_recognition.face_encodings(frame, known_face_locations=face_locations)[0]

            # Load stored student photo
            known_image = face_recognition.load_image_file(student["picture_path"])
            known_encoding = face_recognition.face_encodings(known_image)[0]

            match = face_recognition.compare_faces([known_encoding], captured_encoding)[0]
            break

        cv2.imshow("Face ID Verification", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if match:
        result["status"] = "Present ✅"
        # Save Present record
        with open(ATTENDANCE_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([student_id, student["name"], "Present", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    return jsonify(result)


# ------------------------
# 4. End Class → Auto-Mark Absent
# ------------------------
@app.route("/end_class", methods=["POST"])
def end_class():
    today = date.today().strftime("%Y-%m-%d")

    # Collect students already marked Present today
    marked_present = set()
    with open(ATTENDANCE_FILE, mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "Present" and row["timestamp"].startswith(today):
                marked_present.add(row["student_id"])

    # Mark absent for remaining students
    absents = []
    with open(ATTENDANCE_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        for sid, student in students.items():
            if student["role"] == "Student" and sid not in marked_present:
                writer.writerow([sid, student["name"], "Absent", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                absents.append(student["name"])

    return jsonify({
        "message": "Class ended",
        "absent_students": absents
    })


# ------------------------
# 5. View Attendance Log
# ------------------------
@app.route("/attendance", methods=["GET"])
def get_attendance():
    records = []
    with open(ATTENDANCE_FILE, mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return jsonify(records)


# ------------------------
# Run Flask Server
# ------------------------
if __name__ == "_main_":
    app.run(debug=True)
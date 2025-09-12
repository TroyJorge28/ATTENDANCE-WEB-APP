from flask import Blueprint, jsonify, send_file
import qrcode
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mock_cv2 as cv2
import mock_face_recognition as face_recognition
from datetime import datetime, date
import csv

qr_face = Blueprint('qr_face', __name__, url_prefix='/qr_face')

# Student "DB" (simulate database)
students = {
    "S001": {"name": "Delegate", "picture_path": "delegate.jpg", "role": "Delegate"},
    "S002": {"name": "Bob", "picture_path": "bob.jpg", "role": "Student"},
    "S003": {"name": "Charlie", "picture_path": "charlie.jpg", "role": "Student"},
    "S004": {"name": "Alice", "picture_path": "alice.jpg", "role": "Student"}
}

# Folders and attendance file
QR_FOLDER = "qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)
ATTENDANCE_FILE = "attendance.csv"

# Create attendance file if it doesn't exist
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "name", "status", "timestamp"])

# Store scan order (list of student_ids)
scan_order = []


@qr_face.route("/generate_qr", methods=["POST"])
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


@qr_face.route("/get_scan_order", methods=["GET"])
def get_scan_order():
    return jsonify(scan_order)


# Comment out the face verification function for now
# @qr_face.route("/verify_face/<student_id>", methods=["GET"])
# def verify_face(student_id):
#     # ... function code ...

@qr_face.route("/end_class", methods=["POST"])
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


@qr_face.route("/attendance", methods=["GET"])
def get_attendance():
    records = []
    with open(ATTENDANCE_FILE, mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return jsonify(records)
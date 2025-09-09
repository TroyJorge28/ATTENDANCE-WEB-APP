import random
from datetime import datetime, timedelta

# Temporary OTP storage
otp_storage = {}  # {email: (otp, expiry_time)}

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp(email, otp):
    """Placeholder function to simulate sending OTP"""
    print(f"Sending OTP {otp} to {email}")
    # In real system, integrate smtplib (email) or Twilio (SMS)
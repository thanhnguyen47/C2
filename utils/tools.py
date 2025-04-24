import re
from email.mime.text import MIMEText
import smtplib
from fastapi import HTTPException
from config import SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, SMTP_PORT
from dateutil.parser import parse
import pytz

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def validate_date_of_birth(dob: str) -> str:
    try:
        parsed = parse(dob)
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date of birth format (YYYY-MM-DD)")

def validate_phone_number(phone: str) -> str:
    if not re.match(r"^\+[1-9]\d{1,14}$", phone):
        raise HTTPException(status_code=400, detail="Invalid phone number (must be E.164 format, e.g., +84912345678)")
    return phone

def validate_timezone(tz: str) -> str:
    if tz not in pytz.all_timezones:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    return tz

async def send_verification_email(email: str, token: str):
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    sender_email = SENDER_EMAIL
    sender_password = SENDER_PASSWORD

    verification_url = f"http://127.0.0.1:8000/verify?token={token}" 
    message = MIMEText(f"Nhấn vào liên kết để xác minh email: {verification_url}")
    message["Subject"] = "Xác Minh Email Đăng Ký"
    message["From"] = sender_email
    message["To"] = email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gửi email thất bại: {str(e)}")

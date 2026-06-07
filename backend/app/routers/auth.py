from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EmailVerification

import re
import secrets
import os
import smtplib
from email.message import EmailMessage

router = APIRouter(prefix="/auth", tags=["auth"])

SCHOOL_EMAIL_DOMAIN = "hufs.ac.kr"

def send_verification_email(to_email: str, code: str):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    print("SMTP_USER:", smtp_user)
    print("SMTP_FROM:", smtp_from)
    print("SMTP_PASSWORD_EXISTS:", bool(smtp_password))

    if not smtp_user or not smtp_password:
        raise HTTPException(
            status_code=500,
            detail="SMTP 설정이 누락되었습니다.",
        )

    message = EmailMessage()
    message["Subject"] = "[HUFSOLVE] 학교 이메일 인증번호"
    message["From"] = smtp_from
    message["To"] = to_email
    message.set_content(
        f"""안녕하세요.

HUFSOLVE 학교 이메일 인증번호는 아래와 같습니다.

인증번호: {code}

이 인증번호는 5분 동안 유효합니다.
본인이 요청하지 않았다면 이 메일을 무시해주세요.
"""
    )

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    print(f"[SMTP 발송 완료] {to_email}")


class SendCodeRequest(BaseModel):
    studentId: str
    studentName: str
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    studentId: str
    email: EmailStr
    code: str


@router.post("/send-code")
def send_code(request: SendCodeRequest, db: Session = Depends(get_db)):
    email_pattern = r"^\d{9}@hufs\.ac\.kr$"

    if not re.match(email_pattern, request.email):
        raise HTTPException(
            status_code=400,
            detail="학번 9자리 형식의 학교 이메일만 사용할 수 있습니다.",
        )
    
    email_student_id = request.email.split("@")[0]

    

    if email_student_id != request.studentId:
        raise HTTPException(
            status_code=400,
            detail="입력한 학번과 학교 이메일이 일치하지 않습니다.",
        )
    
    recent_verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.student_id == request.studentId,
            EmailVerification.email == request.email,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if recent_verification:
        recent_created = recent_verification.created_at

        if recent_created.tzinfo is None:
            recent_created = recent_created.replace(tzinfo=timezone.utc)

        seconds = (datetime.now(timezone.utc) - recent_created).total_seconds()

        if seconds < 60:
            raise HTTPException(
                status_code=429,
                detail="인증번호는 1분 뒤 다시 요청해주세요.",
            )

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    verification = EmailVerification(
        student_id=request.studentId,
        student_name=request.studentName,
        email=request.email,
        code=code,
        expires_at=expires_at,
        verified=0,
    )

    db.add(verification)
    db.commit()

    # 실제 메일 전송 전까지는 백엔드 터미널에 인증번호 출력
    print(f"[HUFSOLVE 인증번호] {request.email}: {code}")
    send_verification_email(request.email, code)

    return {"message": "인증번호가 발송되었습니다."}


@router.post("/verify-code")
def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.student_id == request.studentId,
            EmailVerification.email == request.email,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if verification is None:
        raise HTTPException(status_code=404, detail="인증 요청이 없습니다.")

    if verification.verified == 1:
        return {"verified": True}

    expires_at = verification.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="인증번호가 만료되었습니다.")

    if verification.code != request.code:
        raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")

    verification.verified = 1
    db.commit()

    return {"verified": True}

class CheckVerifiedRequest(BaseModel):
    studentId: str
    email: EmailStr

@router.post("/check-verified")
def check_verified(request: CheckVerifiedRequest, db: Session = Depends(get_db)):
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.student_id == request.studentId,
            EmailVerification.email == request.email,
            EmailVerification.verified == 1,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    return {"verified": verification is not None}
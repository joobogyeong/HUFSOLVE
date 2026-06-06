from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EmailVerification

import re

router = APIRouter(prefix="/auth", tags=["auth"])

SCHOOL_EMAIL_DOMAIN = "hufs.ac.kr"


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

    code = str(random.randint(100000, 999999))
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
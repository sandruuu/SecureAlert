from fastapi import APIRouter, Depends, HTTPException, Response, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import datetime
import secrets
import pyotp
import logging
import base64
import json

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
)

from core.config import RP_ID, RP_NAME, ORIGIN
from core.dependencies import get_db, sessions, challenges, mfa_sessions, get_session_data
from core.schemas import RegisterRequest, LoginRequest, MFAVerifyRequest
from core.risk_engine import calculate_risk_score
from models import User, WebAuthnCredential, Device, RegistrationToken, AccessLog, EnrollmentToken
from utils.email import send_otp_email
from passlib.context import CryptContext

router = APIRouter()
logger = logging.getLogger("auth_service.routers.auth")
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def generate_enrollment_token_if_needed(user_id: str, db: Session, current_device: Device = None) -> Optional[str]:
    """
    Check if the current device needs enrollment.
    If current_device is provided:
        - If it has a fingerprint, it's already enrolled. Return None.
        - If it has NO fingerprint, it needs enrollment. Generate Token.
    If current_device is NOT provided (fallback):
        - Check if user has ANY enrolled device. If not, generate token.
    """
    if current_device:
        if current_device.hardware_fingerprint:
            return None # This device is already enrolled
        else:
            # Current device is NOT enrolled, so generate a token for it
            logger.info(f"Generating enrollment token for device {current_device.id} (no fingerprint)")
            enrollment = EnrollmentToken(user_id=user_id, device_id=current_device.id)
            db.add(enrollment)
            db.commit()
            db.refresh(enrollment)
            return enrollment.token

    # Fallback: Check if user has any device with hardware fingerprint
    enrolled_device = db.query(Device).filter(
        Device.user_id == user_id,
        Device.hardware_fingerprint != None
    ).first()
    
    if enrolled_device:
        return None  # User has at least one enrolled device
    
    # User has NO enrolled devices at all
    enrollment = EnrollmentToken(user_id=user_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    logger.info(f"Generated enrollment token for user {user_id} (first device)")
    return enrollment.token

@router.get("/auth")
def check_auth(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        sess_data = sessions[session_id]
        return {
            "username": sess_data["username"], 
            "trust_score": sess_data["score"],
            "role": sess_data.get("role", "user"),
            "status": sess_data.get("status", "active"),
            "enrollment_token": sess_data.get("enrollment_token")
        }
    return Response(status_code=401)

@router.post("/logout")
def logout(request: Request):
    """
    Logout endpoint - removes session from memory and clears cookie.
    """
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
        logger.info(f"Session {session_id} logged out")
    
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("session_id")
    return response


@router.post("/register/options")
def register_options(req: RegisterRequest, db: Session = Depends(get_db)):
    username = req.username
    invite_code = req.invite_code
    
    token_entry = db.query(RegistrationToken).filter(RegistrationToken.token == invite_code).first()
    if not token_entry or token_entry.used or token_entry.expires_at < datetime.datetime.utcnow():
        raise HTTPException(400, "Invalid or expired invitation code")
        
    user = db.query(User).filter(User.id == token_entry.user_id).first()
    if not user or user.username != username:
        raise HTTPException(400, "Username does not match invitation code")
        
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user.id.encode('utf-8'),
        user_name=username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED
        )
    )
    
    challenges[username] = options.challenge
    return Response(content=options_to_json(options), media_type="application/json")

@router.post("/register/verify")
def register_verify(req: RegisterRequest, db: Session = Depends(get_db)):
    username = req.username
    body = req.response
    invite_code = req.invite_code
    
    token_entry = db.query(RegistrationToken).filter(RegistrationToken.token == invite_code).first()
    if not token_entry or token_entry.used:
         raise HTTPException(400, "Invalid code")

    expected_challenge = challenges.pop(username, None)
    if not expected_challenge:
        raise HTTPException(400, "Challenge expired")
        
    verification = verify_registration_response(
        credential=body,
        expected_challenge=expected_challenge,
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID
    )
    
    user = db.query(User).filter(User.username == username).first()
    
    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count
    )
    db.add(cred)
    
    token_entry.used = True
    user.is_active = True
    
    device = Device(user_id=user.id, device_name="Web Device", credential_id=verification.credential_id)
    db.add(device)
    db.commit()
    return {"verified": True}

@router.post("/login/password")
def login_password(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
        
    if not user.is_active:
         raise HTTPException(403, "Account not active")
    
    session_token = f"session_{user.username}_{uuid.uuid4()}"
    sessions[session_token] = {"username": user.username, "score": 50, "method": "password", "role": user.role}
    
    resp = JSONResponse(content={"verified": True, "score": 50, "role": user.role})
    resp.set_cookie("session_id", session_token)
    return resp

@router.post("/login/options")
def login_options(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(404, "User not found")
        
    creds = db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user.id).all()
    descriptors = [PublicKeyCredentialDescriptor(id=c.credential_id, type=PublicKeyCredentialType.PUBLIC_KEY) for c in creds]
        
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=descriptors,
        user_verification=UserVerificationRequirement.PREFERRED
    )
    
    challenges[req.username] = options.challenge
    return Response(content=options_to_json(options), media_type="application/json")

@router.get("/session/status")
def check_session_status(request: Request, db: Session = Depends(get_db)):
    """
    Check current session status (polling endpoint for Login Gate).
    Allows access even if status is 'pending_posture'.
    Checks if posture arrived and updates session.
    """
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    logger.info(f"DEBUG: check_session_status {session_id} -> {user_data.get('status')} score={user_data.get('score')}")
    
    # Check freshness logic...
    
    # Dynamic Check: If pending_posture, check if we received data
    if user_data.get("status") == "pending_posture":
        user_id = user_data.get("user_id")
        if user_id:
             # Check for any device with fresh posture for this user
             # Or shared devices logic (simplified here to user's devices for now)
             user_devices = db.query(Device).filter(Device.user_id == user_id).all()
             for dev in user_devices:
                 if dev.last_posture_time:
                     age = (datetime.datetime.utcnow() - dev.last_posture_time).total_seconds()
                     if age < 120:
                         # Found fresh posture! Upgrade session.
                         # In real world, we would recalculate risk score here.
                         new_score = dev.trust_score if dev.trust_score else 85
                         
                         if new_score >= 80:
                             user_data["status"] = "active"
                             logger.info(f"Session {session_id} upgraded to ACTIVE (Score: {new_score})")
                         elif new_score > 50:
                             user_data["status"] = "mfa_required"
                             logger.info(f"Session {session_id} upgraded to MFA_REQUIRED (Score: {new_score})")
                             
                         user_data["score"] = new_score
                         break

    return {
        "status": user_data.get("status", "active"),
        "score": user_data.get("score"),
        "username": user_data.get("username"),
        "role": user_data.get("role", "user"),
        "enrollment_token": user_data.get("enrollment_token")
    }

@router.post("/login/verify")
def login_verify(req: LoginRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    username = req.username
    body = req.response
    
    expected_challenge = challenges.pop(username, None)
    if not expected_challenge:
        raise HTTPException(400, "Challenge expired")
    credential_id_bytes = base64url_to_bytes(body['id'])
    cred_db = db.query(WebAuthnCredential).filter(WebAuthnCredential.credential_id == credential_id_bytes).first()
    if not cred_db:
         raise HTTPException(400, "Credential not found")
         
    verification = verify_authentication_response(
        credential=body,
        expected_challenge=expected_challenge,
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID,
        credential_public_key=cred_db.public_key,
        credential_current_sign_count=cred_db.sign_count
    )
    
    # --- RISK ENGINE INTEGRATION ---
    
    # 1. Find Device (if linked)
    device = db.query(Device).filter(Device.credential_id == credential_id_bytes).first()
    
    # 2. Build Context
    # In a real deployment, we'd get these from request headers
    # For now, we simulate or take from request if forwarded by proxy
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")
    
    context = {
        "ip_address": client_ip,
        "user_agent": user_agent
    }
    
    user_obj = db.query(User).filter(User.username == username).first()
    
    # Get Last Login for Context
    last_log = db.query(AccessLog).filter(
        AccessLog.user_id == user_obj.id, 
        AccessLog.action == "LOGIN_SUCCESS"
    ).order_by(AccessLog.timestamp.desc()).first()
    
    if last_log:
        context["last_login_ip"] = last_log.ip_address
        context["last_login_time"] = last_log.timestamp

    # 3. Calculate Score
    trust_score, details = calculate_risk_score(user_obj, device, context)
    logger.info(f"Trust Score for {username}: {trust_score}")

    # 4. Decision Logic (Conditional Access)
    # MANDATORY: Agent must be running and reporting fresh posture data
    # Then apply risk-based decisions (MFA / Direct Access / Block)
    
    action = "LOGIN_SUCCESS"
    
    # CHECK: Is device enrolled AND has fresh posture report?
    # Also check for SHARED DEVICE: another user may have enrolled this physical machine
    posture_is_fresh = False
    posture_source_device = None
    
    # First check user's own device
    if device and device.hardware_fingerprint and device.last_posture_time:
        now = datetime.datetime.utcnow()
        age_seconds = (now - device.last_posture_time).total_seconds()
        if age_seconds <= 120:  # 2 minutes freshness
            posture_is_fresh = True
            posture_source_device = device
            logger.info(f"Device {device.id} has fresh posture (age: {age_seconds:.0f}s)")
        else:
            logger.warning(f"Device {device.id} posture stale (age: {age_seconds:.0f}s)")
    
    # If user's device doesn't have fresh posture, check if ANY device with same fingerprint does
    # (Shared device scenario: admin enrolled, now another user logs in)
    if not posture_is_fresh:
        # Look for any enrolled device (any user) with fresh posture
        all_enrolled_devices = db.query(Device).filter(
            Device.hardware_fingerprint != None,
            Device.last_posture_time != None
        ).all()
        
        now = datetime.datetime.utcnow()
        for other_device in all_enrolled_devices:
            if other_device.last_posture_time:
                age_seconds = (now - other_device.last_posture_time).total_seconds()
                if age_seconds <= 120:
                    # Found a device with fresh posture - use its posture data
                    posture_is_fresh = True
                    posture_source_device = other_device
                    logger.info(f"Using shared device {other_device.id} posture for user {username} (fingerprint: {other_device.hardware_fingerprint})")
                    
                    # If current user doesn't have a device, create one linked to this fingerprint
                    if not device:
                        device = Device(
                            user_id=user_obj.id,
                            credential_id=credential_id_bytes,
                            device_name=f"{other_device.hardware_fingerprint.split(':')[0]} (Shared)",
                            hardware_fingerprint=other_device.hardware_fingerprint,
                            device_secret=other_device.device_secret,  # Share the secret for HMAC
                            last_posture_report=other_device.last_posture_report,
                            last_posture_time=other_device.last_posture_time,
                            trust_score=50
                        )
                        db.add(device)
                        db.commit()
                        db.refresh(device)
                        logger.info(f"Created linked device {device.id} for user {username}")
                    else:
                        # User has a device but with stale posture - update it from shared device
                        device.last_posture_report = other_device.last_posture_report
                        device.last_posture_time = other_device.last_posture_time
                        db.commit()
                        logger.info(f"Updated device {device.id} posture from shared device {other_device.id}")
                    break
    
    # RECALCULATE score if we found a shared device with fresh posture
    if posture_is_fresh and posture_source_device:
        trust_score, details = calculate_risk_score(user_obj, device, context)
        logger.info(f"Recalculated Trust Score for {username}: {trust_score} (using fresh posture)")
    
    # CASE 0: Agent NOT active -> Always require posture first
    # This is MANDATORY regardless of risk score
    if not posture_is_fresh:
        logger.warning(f"Posture Check Required for {username}. Score: {trust_score}")
        
        # Log as PENDING
        db.add(AccessLog(
            user_id=user_obj.id,
            device_id=device.id if device else None,
            risk_score_at_time=trust_score,
            action="POSTURE_REQUIRED",
            ip_address=client_ip,
            user_agent=user_agent,
            timestamp=datetime.datetime.utcnow()
        ))
        db.commit()
        
        # Generate Token FIRST
        enrollment_token = generate_enrollment_token_if_needed(user_obj.id, db, device)

        # Create Restricted Session
        session_token = f"session_{username}_{uuid.uuid4()}"
        sessions[session_token] = {
            "username": username, 
            "score": trust_score, 
            "method": "fido2", 
            "role": user_obj.role, 
            "user_id": user_obj.id,
            "status": "pending_posture",
            "enrollment_token": enrollment_token
        }
        
        resp = JSONResponse(content={
            "verified": True,
            "status": "posture_required",
            "enrollment_token": enrollment_token,
            "score": trust_score
        })
        resp.set_cookie("session_id", session_token)
        return resp

    # --- AGENT IS ACTIVE, apply risk-based decisions ---
    
    # CASE 1: Very Low Trust -> BLOCK
    if trust_score <= 50:
        logger.warning(f"Access BLOCKED for {username}. Score too low: {trust_score}")
        db.add(AccessLog(
            user_id=user_obj.id,
            device_id=device.id if device else None,
            risk_score_at_time=trust_score,
            action="BLOCKED",
            ip_address=client_ip,
            user_agent=user_agent,
            timestamp=datetime.datetime.utcnow()
        ))
        db.commit()
        raise HTTPException(403, f"Access denied. Trust score too low: {trust_score}")
    
    # CASE 2: Medium Trust -> MFA Required
    if 50 < trust_score < 80:
        # STEP-UP AUTH (MFA)
        logger.info(f"MFA Required for {username}. Score: {trust_score}")
        
        temp_token = secrets.token_hex(16)
        mfa_type = "email"
        if user_obj.mfa_enabled and user_obj.mfa_secret:
            mfa_type = "totp"
        else:
            otp_code = secrets.token_hex(3).upper()
            mfa_sessions[temp_token] = {
                "username": username, 
                "code": otp_code, 
                "type": "email", 
                "score": trust_score,
                "expires": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
            }
            background_tasks.add_task(send_otp_email, username, otp_code)
            
        if mfa_type == "totp":
             mfa_sessions[temp_token] = {
                 "username": username, 
                 "type": "totp", 
                 "score": trust_score,
                 "expires": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
             }
             
        # Log Challenge
        db.add(AccessLog(
            user_id=user_obj.id,
            device_id=device.id if device else None,
            risk_score_at_time=trust_score,
            action="MFA_CHALLENGE",
            ip_address=client_ip,
            user_agent=user_agent,
            timestamp=datetime.datetime.utcnow()
        ))
        db.commit()

        return JSONResponse(content={
            "verified": False, 
            "mfa_required": True, 
            "mfa_type": mfa_type, 
            "temp_token": temp_token,
            "trust_score": trust_score 
        })

    # CASE 3: High Trust -> Active
    # SCORE >= 75: DIRECT ACCESS
    cred_db.sign_count = verification.new_sign_count
    
    # Update Device Data
    if not device:
        logger.info("New Device registered.")
        device = Device(
            user_id=cred_db.user_id,
            credential_id=credential_id_bytes,
            device_name=f"New Device ({datetime.datetime.utcnow().strftime('%Y-%m-%d')})",
            trust_score=trust_score,
            last_posture_report=json.dumps({"detected": True}) 
        )
        db.add(device)
    else:
        device.trust_score = trust_score
    
    # Log Success
    db.add(AccessLog(
        user_id=cred_db.user_id,
        device_id=device.id,
        risk_score_at_time=trust_score,
        action="LOGIN_SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        timestamp=datetime.datetime.utcnow()
    ))
    db.commit()
    
    session_token = f"session_{username}_{uuid.uuid4()}"
    sessions[session_token] = {
        "username": username, 
        "score": trust_score, 
        "method": "fido2", 
        "role": user_obj.role, 
        "user_id": user_obj.id,
        "status": "active"
    }
    
    # Return Active Status
    resp = JSONResponse(content={
        "verified": True, 
        "status": "active", 
        "score": trust_score, 
        "role": user_obj.role
    })
    resp.set_cookie("session_id", session_token)
    return resp

@router.post("/auth/mfa/verify")
def verify_mfa_code(req: MFAVerifyRequest, db: Session = Depends(get_db)):
    if req.temp_token not in mfa_sessions:
        raise HTTPException(400, "Invalid or expired session")
        
    session_data = mfa_sessions[req.temp_token]
    if session_data["expires"] < datetime.datetime.utcnow():
        del mfa_sessions[req.temp_token]
        raise HTTPException(400, "Code expired")
        
    user = db.query(User).filter(User.username == session_data["username"]).first()
    
    if session_data["type"] == "email":
        if session_data["code"] != req.code.upper():
             raise HTTPException(400, "Invalid code")
    elif session_data["type"] == "totp":
        if not pyotp.TOTP(user.mfa_secret).verify(req.code):
             raise HTTPException(400, "Invalid Authenticator code")
             
    del mfa_sessions[req.temp_token]
    session_token = f"session_{user.username}_{uuid.uuid4()}"
    final_score = session_data.get("score", 90)
    
    sessions[session_token] = {
        "username": user.username, 
        "score": final_score, 
        "method": "mfa", 
        "role": user.role,
        "user_id": user.id,
        "status": "active"
    }
    
    resp = JSONResponse(content={
        "verified": True, 
        "role": user.role, 
        "status": "active",
        "username": user.username,
        "score": final_score
    })
    resp.set_cookie("session_id", session_token)
    return resp

@router.post("/auth/mfa/challenge")
def request_mfa_challenge(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    if user_data.get("status") != "mfa_required":
        raise HTTPException(status_code=400, detail="MFA not required")
    
    username = user_data["username"]
    user_obj = db.query(User).filter(User.username == username).first()
    
    # Generate MFA Challenge
    temp_token = secrets.token_hex(16)
    mfa_type = "email"
    if user_obj.mfa_enabled and user_obj.mfa_secret:
        mfa_type = "totp"
    else:
        otp_code = secrets.token_hex(3).upper()
        # In background for production, but here synchronous for simplicity/debug
        try:
           send_otp_email(username, otp_code)
        except Exception as e:
           logger.error(f"Failed to send email: {e}")
           
        mfa_sessions[temp_token] = {
            "username": username, 
            "code": otp_code, 
            "type": "email", 
            "score": user_data.get("score", 50),
            "expires": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }
        
    if mfa_type == "totp":
         mfa_sessions[temp_token] = {
             "username": username, 
             "type": "totp", 
             "score": user_data.get("score", 50),
             "expires": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
         }
         
    return {
        "mfa_required": True,
        "mfa_type": mfa_type,
        "temp_token": temp_token
    }

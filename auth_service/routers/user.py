from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
import io
import base64
import qrcode
import pyotp
import hmac
import hashlib
import datetime
import json
import logging
from webauthn import generate_registration_options, verify_registration_response, options_to_json
from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement, PublicKeyCredentialDescriptor, PublicKeyCredentialType

from core.config import RP_ID, RP_NAME, ORIGIN
from core.dependencies import get_db, get_current_user, challenges, sessions
from core.schemas import MFAActivateRequest, RegisterRequest, PostureReportRequest
from core.risk_engine import evaluate_posture_change
from models import User, WebAuthnCredential, Device, PostureEvent

logger = logging.getLogger("auth_service.routers.user")

# Nonce cache to prevent replay attacks (in production, use Redis with TTL)
used_nonces = set()

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/mfa/setup")
def mfa_setup(user_data: dict = Depends(get_current_user)):
    username = user_data["username"]
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="SecureAlert")
    
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return {"secret": secret, "qr_code": f"data:image/png;base64,{qr_b64}"}

@router.post("/mfa/activate")
def mfa_activate(req: MFAActivateRequest, user_data: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not pyotp.TOTP(req.secret).verify(req.code):
        raise HTTPException(400, "Invalid code")
        
    user = db.query(User).filter(User.username == user_data["username"]).first()
    user.mfa_secret = req.secret
    user.mfa_enabled = True
    db.commit()
    return {"message": "MFA Activated"}

@router.get("/device/credentials")
def get_device_credentials(user_data: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns device credentials for the posture agent.
    The agent can use this endpoint to automatically obtain device_id and device_secret
    instead of requiring manual configuration.
    """
    user = db.query(User).filter(User.username == user_data["username"]).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Get the most recent device for this user
    device = db.query(Device).filter(Device.user_id == user.id).order_by(Device.id.desc()).first()
    
    if not device:
        raise HTTPException(404, "No device found. Please complete registration first.")
    
    logger.info(f"Posture agent credentials requested for user {user.username}, device {device.id}")
    
    return {
        "device_id": device.id,
        "device_secret": device.device_secret,
        "device_name": device.device_name
    }

@router.post("/devices/register/options")
def register_device_options(user_data: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data["username"]).first()
    creds = db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user.id).all()
    exclude = [PublicKeyCredentialDescriptor(id=c.credential_id, type=PublicKeyCredentialType.PUBLIC_KEY) for c in creds]
    
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user.id.encode('utf-8'),
        user_name=user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(user_verification=UserVerificationRequirement.PREFERRED)
    )
    
    challenges[user.username] = options.challenge
    return Response(content=options_to_json(options), media_type="application/json")

@router.post("/devices/register/verify")
def register_device_verify(req: RegisterRequest, user_data: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    username = user_data["username"]
    expected_challenge = challenges.pop(username, None)
    if not expected_challenge:
        raise HTTPException(400, "Challenge expired")
        
    verification = verify_registration_response(
        credential=req.response,
        expected_challenge=expected_challenge,
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID
    )
    
    user = db.query(User).filter(User.username == username).first()
    db.add(WebAuthnCredential(
        user_id=user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count
    ))
    
    device_count = db.query(Device).filter(Device.user_id == user.id).count()
    db.add(Device(user_id=user.id, device_name=f"Device {device_count + 1}", credential_id=verification.credential_id))
    db.commit()
    return {"verified": True}


def verify_hmac_signature(device_secret: str, device_id: str, timestamp: int, nonce: str, posture: dict, signature: str) -> bool:
    """Verify HMAC-SHA256 signature of posture report"""
    # Construct the message to sign (deterministic JSON)
    message = f"{device_id}:{timestamp}:{nonce}:{json.dumps(posture, sort_keys=True)}"
    expected_sig = hmac.new(device_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    logger.info(f"HMAC Debug - Message: {message[:100]}...")
    logger.info(f"HMAC Debug - Expected: {expected_sig[:20]}... Received: {signature[:20]}...")
    
    return hmac.compare_digest(expected_sig, signature)


def invalidate_user_sessions(user_id: str, reason: str):
    """Invalidate all sessions for a user"""
    to_remove = [sid for sid, data in sessions.items() if data.get("user_id") == user_id]
    for sid in to_remove:
        del sessions[sid]
        logger.warning(f"Session {sid} invalidated: {reason}")
    return len(to_remove)


@router.post("/posture/report")
def report_posture(req: PostureReportRequest, db: Session = Depends(get_db)):
    """
    Endpoint for posture agent to report device health.
    Validates HMAC signature and evaluates posture.
    If posture fails, invalidates user's sessions.
    """
    # 1. Find device
    device = db.query(Device).filter(Device.id == req.device_id).first()
    if not device:
        raise HTTPException(404, "Device not found")
    
    # 2. Check timestamp (max 60s old)
    now = int(datetime.datetime.utcnow().timestamp())
    if abs(now - req.timestamp) > 60:
        raise HTTPException(400, "Timestamp expired or invalid")
    
    # 3. Check nonce (replay protection)
    if req.nonce in used_nonces:
        raise HTTPException(400, "Nonce already used (replay attack detected)")
    used_nonces.add(req.nonce)
    # Cleanup old nonces (keep set manageable)
    if len(used_nonces) > 10000:
        used_nonces.clear()
    
    # 4. Verify HMAC signature
    if not verify_hmac_signature(device.device_secret, req.device_id, req.timestamp, req.nonce, req.posture, req.signature):
        logger.warning(f"Invalid HMAC signature for device {req.device_id}")
        raise HTTPException(403, "Invalid signature")
    
    # 5. Update device posture record
    device.last_posture_report = json.dumps(req.posture)
    device.last_posture_time = datetime.datetime.utcnow()
    db.commit()
    
    # 6. Recalculate FULL risk score (not just posture check)
    from core.risk_engine import calculate_risk_score
    from models import User
    
    user = db.query(User).filter(User.id == device.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Build context for risk calculation
    context = {
        "ip_address": None,  # Agent reports don't include IP context
        "user_agent": "PostureAgent/1.0",
        "last_login_ip": None,
        "last_login_time": None
    }
    
    trust_score, details = calculate_risk_score(user, device, context)
    
    # 7. Decision: if score <= 50, disconnect
    should_disconnect = trust_score <= 50
    reason = None
    
    if should_disconnect:
        reason = f"Trust score dropped to {trust_score} (threshold: 60). Details: {details}"
    
    # 8. Log event
    event_type = "SESSION_TERMINATED" if should_disconnect else "POSTURE_OK"
    event = PostureEvent(
        user_id=device.user_id,
        device_id=device.id,
        event_type=event_type,
        reason=reason,
        posture_snapshot=json.dumps({"posture": req.posture, "score": trust_score, "details": details})
    )
    db.add(event)
    db.commit()
    
    # 9. If score <= 50, invalidate sessions
    if should_disconnect:
        count = invalidate_user_sessions(device.user_id, reason)
        logger.warning(f"Trust score {trust_score} <= 50 for device {req.device_id}. Invalidated {count} sessions.")
    else:
        # Update score in active sessions (allows Polling Endpoint to see improvement)
        for sid, data in sessions.items():
            if data.get("user_id") == device.user_id:
                data["score"] = trust_score
                
                # PROMOTE SESSION STATUS based on new score
                if trust_score >= 75:
                    data["status"] = "active"
                    logger.info(f"Promoted session {sid} to ACTIVE (Score: {trust_score})")
                elif 55 <= trust_score < 75:
                     # If it was pending, maybe we require MFA now? 
                     # For simplicity in this fix, if we are recovering, let's allow active if MFA was done?
                     # Or stick to logic: Medium Trust -> MFA.
                     if data.get("status") == "pending_posture":
                         data["status"] = "mfa_required"
                         logger.info(f"Promoted session {sid} to MFA_REQUIRED (Score: {trust_score})")
                
                logger.info(f"Updated session {sid} score to {trust_score}")
    
    return {"status": "ok", "trust_score": trust_score, "details": details}

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
import secrets

from core.dependencies import get_db, require_admin
from core.schemas import CreateUserRequest, UpdateUserStatusRequest
from models import User, RegistrationToken, WebAuthnCredential, Device, AccessLog
from utils.email import send_invite_email

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id, 
            "username": u.username, 
            "full_name": u.full_name, 
            "role": u.role, 
            "is_active": u.is_active,
            "has_mfa": len(u.credentials) > 0
        } 
        for u in users
    ]

@router.post("/users")
def create_user(req: CreateUserRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "Username already exists")
        
    new_user = User(username=req.username, full_name=req.full_name, role=req.role, is_active=False)
    db.add(new_user)
    db.flush()
    
    invite_code = secrets.token_hex(4)
    token = RegistrationToken(token=invite_code, user_id=new_user.id)
    db.add(token)
    db.commit()
    
    background_tasks.add_task(send_invite_email, req.username, invite_code)
    return {"message": "User created & Email queued", "invite_code": invite_code}

@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
        
    # Get current user from dependencies (it's already checked by require_admin prefix in main but let's be safe)
    # Actually sessions is imported in dependencies.
    from core.dependencies import sessions
    session_id = request.cookies.get("session_id")
    if user.username == sessions[session_id]["username"]:
         raise HTTPException(400, "Cannot delete yourself")
         
    db.query(RegistrationToken).filter(RegistrationToken.user_id == user.id).delete()
    db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == user.id).delete()
    
    # CRITICAL: Delete AccessLog AND PostureEvent (children) before Device (parent)
    from models import PostureEvent
    db.query(AccessLog).filter(AccessLog.user_id == user.id).delete()
    db.query(PostureEvent).filter(PostureEvent.user_id == user.id).delete()
    db.query(Device).filter(Device.user_id == user.id).delete()
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

@router.patch("/users/{user_id}/status")
def update_user_status(user_id: str, req: UpdateUserStatusRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
        
    from core.dependencies import sessions
    session_id = request.cookies.get("session_id")
    if user.username == sessions[session_id]["username"] and req.is_active is False:
         raise HTTPException(400, "Cannot deactivate yourself")

    user.is_active = req.is_active
    db.commit()
    return {"message": "Status updated", "is_active": user.is_active}

@router.post("/users/{user_id}/reset-invite")
def reset_invite(user_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
        
    db.query(RegistrationToken).filter(RegistrationToken.user_id == user.id).delete()
    invite_code = secrets.token_hex(4)
    db.add(RegistrationToken(token=invite_code, user_id=user.id))
    db.commit()
    
    background_tasks.add_task(send_invite_email, user.username, invite_code)
    return {"message": "Invite regenerated & Email queued", "invite_code": invite_code}

@router.get("/logs")
def list_logs(db: Session = Depends(get_db)):
    from models import PostureEvent
    
    # Get access logs
    access_logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(50).all()
    
    # Get posture events
    posture_events = db.query(PostureEvent).order_by(PostureEvent.timestamp.desc()).limit(50).all()
    
    result = []
    
    # Add access logs
    for log in access_logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        username = user.username if user else "Unknown"
        
        result.append({
            "id": log.id,
            "username": username,
            "action": log.action,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat(),
            "risk_score": log.risk_score_at_time,
            "device_id": log.device_id,
            "event_source": "AUTH"
        })
    
    # Add posture events
    for event in posture_events:
        user = db.query(User).filter(User.id == event.user_id).first()
        username = user.username if user else "Unknown"
        
        result.append({
            "id": event.id,
            "username": username,
            "action": event.event_type,
            "ip_address": None,
            "timestamp": event.timestamp.isoformat(),
            "risk_score": None,
            "device_id": event.device_id,
            "reason": event.reason,
            "event_source": "POSTURE"
        })
    
    # Sort by timestamp descending
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return result[:100]  # Limit total to 100

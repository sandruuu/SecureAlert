from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
import database
from typing import Dict

sessions: Dict[str, dict] = {}
challenges: Dict[str, str] = {}
mfa_sessions: Dict[str, dict] = {}

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session_data(request: Request):
    """
    Get session data without enforcing active status.
    Used for polling session status during login/MFA.
    """
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[session_id]

def get_current_user(user_data: dict = Depends(get_session_data)):
    """
    Get current user AND enforce active session status.
    Used for protected routes (dashboard, etc).
    """
    status = user_data.get("status", "active") # Default to active for backward compatibility
    
    # print(f"DEBUG: Checking session {user_data.get('username')} status: {status}")
    if status == "pending_posture":
        raise HTTPException(status_code=403, detail="Posture check required")
    if status == "mfa_required":
        raise HTTPException(status_code=403, detail="MFA required")
    if status == "blocked":
        raise HTTPException(status_code=403, detail=user_data.get("block_reason", "Account blocked"))
        
    return user_data

def require_admin(user_data: dict = Depends(get_current_user)):
    if user_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_data

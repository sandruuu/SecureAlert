"""
Agent enrollment router - handles posture agent registration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import datetime
import logging

from core.dependencies import get_db
from models import User, Device, EnrollmentToken, AccessLog, PostureEvent

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger("auth_service.routers.agent")


class EnrollRequest(BaseModel):
    token: str
    hardware_fingerprint: str


@router.post("/enroll")
def enroll_agent(req: EnrollRequest, db: Session = Depends(get_db)):
    """
    Enroll a posture agent using a one-time enrollment token.
    Returns device_id and device_secret for the agent to use.
    """
    # 1. Validate token
    enrollment = db.query(EnrollmentToken).filter(
        EnrollmentToken.token == req.token,
        EnrollmentToken.used == False
    ).first()
    
    if not enrollment:
        raise HTTPException(400, "Invalid or already used enrollment token")
    
    if enrollment.expires_at < datetime.datetime.utcnow():
        raise HTTPException(400, "Enrollment token expired")
    
    # 2. Mark token as used
    enrollment.used = True
    
    # 3. Handle device linking and duplicates
    # Case A: We have a shell device pre-assigned by the token (Robust Linking)
    shell_device = None
    if enrollment.device_id:
        shell_device = db.query(Device).filter(Device.id == enrollment.device_id).first()
        if shell_device:
            logger.info(f"Using pre-assigned shell device {shell_device.id} from token")

    # Case B: Find if ANOTHER device with this fingerprint exists for the user
    existing_fp_device = db.query(Device).filter(
        Device.user_id == enrollment.user_id,
        Device.hardware_fingerprint == req.hardware_fingerprint
    ).first()

    hostname = req.hardware_fingerprint.split(":")[0] if ":" in req.hardware_fingerprint else "Agent Device"

    if shell_device:
        # We MUST use the shell device to satisfy the current login session
        if existing_fp_device and existing_fp_device.id != shell_device.id:
            logger.warning(f"Merging: Transferring data from existing agent device {existing_fp_device.id} to shell {shell_device.id}")
            
            # Transfer dependencies to keep history and avoid FK errors
            db.query(AccessLog).filter(AccessLog.device_id == existing_fp_device.id).update({"device_id": shell_device.id})
            db.query(PostureEvent).filter(PostureEvent.device_id == existing_fp_device.id).update({"device_id": shell_device.id})
            db.query(EnrollmentToken).filter(EnrollmentToken.device_id == existing_fp_device.id).update({"device_id": shell_device.id})
            
            db.delete(existing_fp_device)
            db.flush() # Ensure deletion is staged before linking
        
        logger.info(f"Linking Agent {hostname} to Shell Device {shell_device.id}")
        shell_device.hardware_fingerprint = req.hardware_fingerprint
        shell_device.device_name = f"{hostname} (Linked)"
        new_device = shell_device
    elif existing_fp_device:
        # Fallback for tokens without device_id (legacy)
        logger.info(f"Re-enrolling existing device {existing_fp_device.id}")
        new_device = existing_fp_device
    else:
        # Check for any "shell" device without fingerprint as a last resort
        fallback_shell = db.query(Device).filter(
            Device.user_id == enrollment.user_id,
            Device.hardware_fingerprint == None
        ).order_by(Device.id.desc()).first()

        if fallback_shell:
             logger.info(f"Linking to fallback shell device {fallback_shell.id}")
             fallback_shell.hardware_fingerprint = req.hardware_fingerprint
             fallback_shell.device_name = f"{hostname} (Linked)"
             new_device = fallback_shell
        else:
            logger.info(f"Creating NEW Device for Agent {hostname}")
            new_device = Device(
                user_id=enrollment.user_id,
                device_name=f"Agent - {hostname}",
                hardware_fingerprint=req.hardware_fingerprint
            )
            db.add(new_device)
    
    db.commit()
    db.refresh(new_device)
    
    # Get user for logging
    user = db.query(User).filter(User.id == enrollment.user_id).first()
    logger.info(f"New agent enrolled: device {new_device.id} for user {user.username if user else enrollment.user_id}")
    
    return {
        "status": "ok",
        "device_id": new_device.id,
        "device_secret": new_device.device_secret,
        "device_name": new_device.device_name,
        "message": "Device enrolled successfully"
    }


@router.get("/check/{hardware_fingerprint}")
def check_enrollment(hardware_fingerprint: str, db: Session = Depends(get_db)):
    """
    Check if a device with given fingerprint is already enrolled.
    Used by agent to check if it needs to enroll.
    """
    device = db.query(Device).filter(
        Device.hardware_fingerprint == hardware_fingerprint
    ).first()
    
    if device:
        return {
            "enrolled": True,
            "device_id": device.id,
            "device_secret": device.device_secret,
            "device_name": device.device_name
        }
    
    return {"enrolled": False}

from pydantic import BaseModel
from typing import Optional, Dict, List

class RegisterRequest(BaseModel):
    username: str
    response: Optional[dict] = None
    invite_code: Optional[str] = None

class CreateUserRequest(BaseModel):
    username: str
    full_name: str
    role: str = "user"

class UpdateUserStatusRequest(BaseModel):
    is_active: bool

class LoginRequest(BaseModel):
    username: str
    password: Optional[str] = None
    response: Optional[dict] = None

class MFAVerifyRequest(BaseModel):
    temp_token: str
    code: str

class MFAActivateRequest(BaseModel):
    secret: str
    code: str

class PostureReportRequest(BaseModel):
    device_id: str
    timestamp: int  # Unix timestamp
    nonce: str  # UUID for replay protection
    posture: dict  # {firewall_enabled, antivirus_enabled, os_version, os_healthy}
    signature: str  # HMAC-SHA256 signature

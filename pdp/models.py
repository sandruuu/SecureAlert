from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, LargeBinary, Text
from sqlalchemy.orm import relationship, declarative_base
import uuid
import datetime
import secrets

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    
    devices = relationship("Device", back_populates="user")
    credentials = relationship("WebAuthnCredential", back_populates="user")
    registration_tokens = relationship("RegistrationToken", back_populates="user")

class RegistrationToken(Base):
    __tablename__ = "registration_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=24))
    
    user = relationship("User", back_populates="registration_tokens")

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    credential_id = Column(LargeBinary, unique=True) # Stored as bytes
    public_key = Column(LargeBinary)
    sign_count = Column(Integer, default=0)
    
    user = relationship("User", back_populates="credentials")

class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    credential_id = Column(LargeBinary, nullable=True) # Linked credential
    device_name = Column(String)
    wireguard_pubkey = Column(String, nullable=True)
    assigned_vpn_ip = Column(String, nullable=True)
    
    # Thesis Requirements
    trust_score = Column(Integer, default=0) # Last calculated score
    posture_baseline = Column(Text, default="{}") # JSON: Ideal state
    last_posture_report = Column(Text, default="{}") # JSON: Actual state from agent
    last_posture_time = Column(DateTime, nullable=True) # When last report was received
    
    # HMAC Signing Secret (unique per device)
    device_secret = Column(String, default=lambda: str(uuid.uuid4()))
    
    # Hardware fingerprint for auto-enrollment (hostname + hardware ID)
    hardware_fingerprint = Column(String, nullable=True, index=True)
    
    user = relationship("User", back_populates="devices")

class Resource(Base):
    __tablename__ = "resources"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    type = Column(String) # 'WEB' or 'NETWORK'
    internal_address = Column(String)
    min_trust_score = Column(Integer, default=80)

class AccessLog(Base):
    __tablename__ = "access_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    device_id = Column(String, ForeignKey("devices.id"), nullable=True)
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    risk_score_at_time = Column(Integer)
    
    action = Column(String) # LOGIN_SUCCESS, MFA_CHALLENGE, BLOCKED
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class PostureEvent(Base):
    """Logs posture verification events for admin monitoring"""
    __tablename__ = "posture_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    device_id = Column(String, ForeignKey("devices.id"), nullable=True)
    
    event_type = Column(String)  # POSTURE_OK, POSTURE_VIOLATION, SESSION_TERMINATED
    reason = Column(String, nullable=True)  # "Firewall disabled", "Antivirus missing"
    posture_snapshot = Column(Text, nullable=True)  # JSON snapshot of posture at time of event
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class EnrollmentToken(Base):
    """One-time tokens for posture agent enrollment"""
    __tablename__ = "enrollment_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    device_id = Column(String, ForeignKey("devices.id"), nullable=True) # CHANGED: Link token to specific device
    token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(32))
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(minutes=10))
    
    user = relationship("User")

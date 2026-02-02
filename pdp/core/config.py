import os

# SMTP CONFIGURATION
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "laura.maris104121@gmail.com"
SMTP_PASSWORD = "eouq bepn qnel wuxv" # App Password

# WEBAUTHN CONFIGURATION
RP_ID = "localhost"
RP_NAME = "Zero Trust Gateway"
ORIGIN = "http://localhost:8080"

# SESSION CONFIGURATION
SESSION_EXPIRE_MINUTES = 60
MFA_EXPIRE_MINUTES = 5

# DATABASE
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/auth_db")

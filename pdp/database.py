from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import time
import traceback

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/zerotrust_db")

print(f"LOG: Database URL is {DATABASE_URL}")

try:
    engine = create_engine(
        DATABASE_URL, 
        pool_pre_ping=True,
        connect_args={'connect_timeout': 5}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("LOG: SQLAlchemy engine and sessionmaker created.")
except Exception as e:
    print(f"ERROR: Failed to create engine: {e}")
    traceback.print_exc()

def init_db():
    print("LOG: init_db() starting...")
    try:
        import models
        from passlib.context import CryptContext
        
        print("LOG: models.py imported successfully.")
        models.Base.metadata.create_all(bind=engine)
        print("LOG: Base.metadata.create_all(bind=engine) COMPLETED.")

        # --- SEED ADMIN ---
        import sys
        db = SessionLocal()
        print("LOG: Checking for existing admin user...", file=sys.stderr)
        try:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_user = db.query(models.User).filter(models.User.username == admin_username).first()
            if not admin_user:
                print(f"LOG: Admin user '{admin_username}' not found. Seeding default admin...", file=sys.stderr)
                pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
                admin = models.User(
                    username=admin_username, 
                    full_name="System Administrator",
                    role="admin", 
                    is_active=True,
                    password_hash=pwd_context.hash("admin123")
                )
                db.add(admin)
                db.flush()  # Get admin.id
                
                # Create invitation code for admin to register FIDO2 key
                import secrets
                invite_code = secrets.token_hex(4).upper()
                invite_token = models.RegistrationToken(
                    user_id=admin.id,
                    token=invite_code
                )
                db.add(invite_token)
                db.commit()
                print(f"LOG: Default admin created (user: {admin_username})", file=sys.stderr)
                print(f"LOG: Admin invitation code: {invite_code}", file=sys.stderr)
                
                # Send invite email to admin
                try:
                    from utils.email import send_invite_email
                    send_invite_email(admin_username, invite_code)
                    print(f"LOG: Invite email sent to {admin_username}", file=sys.stderr)
                except Exception as email_err:
                    print(f"WARNING: Could not send invite email: {email_err}", file=sys.stderr)
            else:
                print(f"LOG: Admin user found: {admin_user.username}", file=sys.stderr)
        except Exception as se:
            print(f"ERROR: Seeding failed: {se}", file=sys.stderr)
            traceback.print_exc()
        finally:
            db.close()

    except Exception as e:
        print(f"ERROR: init_db() failed: {e}")
        traceback.print_exc()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

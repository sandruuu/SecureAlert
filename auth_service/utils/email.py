import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from core.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

logger = logging.getLogger("auth_service .utils.email")

def send_email(to_email: str, subject: str, html_content: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"SecureAlert <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        logger.info(f"Sending email to {to_email}...")
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_invite_email(to_email: str, invite_code: str):
    subject = "🔐 SecureAlert - Registration Invitation"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #4F46E5;">Welcome to SecureAlert!</h2>
                <p>You have been invited to register your device.</p>
                <p>Please use the following <strong>Invite Code</strong>:</p>
                <div style="background-color: #f3f4f6; padding: 15px; text-align: center; border-radius: 5px; font-size: 24px; font-weight: bold; letter-spacing: 2px;">
                    {invite_code}
                </div>
                <p style="margin-top: 20px;">Use this code along with your email address (<b>{to_email}</b>) to register.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #888;">If you did not expect this email, please ignore it.</p>
            </div>
        </body>
    </html>
    """
    return send_email(to_email, subject, html_content)

def send_otp_email(to_email: str, otp_code: str):
    subject = "🔐 SecureAlert - Login Verification"
    html_content = f"<h2>Verification Code: {otp_code}</h2><p>This code expires in 5 minutes.</p>"
    return send_email(to_email, subject, html_content)

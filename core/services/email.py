import os
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import dotenv

dotenv.load_dotenv()


class EmailParams(BaseModel):
    subject: str
    body: str
    to_email: EmailStr
    from_email: EmailStr


def send_email(params: EmailParams):
    """
    Send an email via SMTP.

    :param params: Email parameters
    """
    server = None

    smtp_server = os.getenv("REQURV_SMTP_SERVER") or "smtp.example.com"
    smtp_user = os.getenv("REQURV_SMTP_USER") or "user@example.com"
    smtp_password = os.getenv("REQURV_SMTP_KEY") or "password"
    
    try:
        # Connect to the server
        server = smtplib.SMTP(smtp_server, 587)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)

        # Create a multipart message
        msg = MIMEMultipart()
        msg["From"] = params.from_email
        msg["To"] = params.to_email
        msg["Subject"] = params.subject

        # Attach the body with the msg instance
        msg.attach(MIMEText(params.body, "plain"))

        # Send the email
        server.sendmail(params.from_email, params.to_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        # Terminate the SMTP session
        if server:
            server.quit()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email using SMTP"""
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def generate_invitation_email(full_name: str, invitation_url: str, inviter_name: str) -> str:
    """Generate HTML content for invitation email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
            }}
            .content {{
                background-color: white;
                padding: 25px;
                border-radius: 6px;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .button:hover {{
                background-color: #2980b9;
            }}
            .footer {{
                text-align: center;
                color: #7f8c8d;
                font-size: 12px;
                margin-top: 20px;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Claim Chaser</h1>
                <p style="color: #667eea; font-size: 14px; margin: 5px 0 0 0;">Maximized Revenue</p>
            </div>
            <div class="content">
                <h2>Welcome to Claim Chaser!</h2>
                <p>Hi {full_name},</p>
                <p><strong>{inviter_name}</strong> has invited you to join Claim Chaser by Maximized Revenue, our claims tracking and management platform.</p>
                <p>To get started, please click the button below to set up your password and activate your account:</p>
                <div style="text-align: center;">
                    <a href="{invitation_url}" class="button">Set Up Your Password</a>
                </div>
                <div class="warning">
                    <strong>⏰ Important:</strong> This invitation link will expire in 48 hours.
                </div>
                <p>If you didn't expect this invitation, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                <p>This is an automated email from Claim Chaser by Maximized Revenue.</p>
                <p>Please do not reply to this email. If you have questions, contact your administrator.</p>
                <p style="margin-top: 10px;">Email: claimchaser@maximizedrevenue.com</p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_password_reset_email(full_name: str, reset_url: str) -> str:
    """Generate HTML content for password reset email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
            }}
            .content {{
                background-color: white;
                padding: 25px;
                border-radius: 6px;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #e74c3c;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                color: #7f8c8d;
                font-size: 12px;
                margin-top: 20px;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Claim Chaser</h1>
                <p style="color: #667eea; font-size: 14px; margin: 5px 0 0 0;">Maximized Revenue</p>
            </div>
            <div class="content">
                <h2>Password Reset Request</h2>
                <p>Hi {full_name},</p>
                <p>We received a request to reset your password. Click the button below to set a new password:</p>
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                <div class="warning">
                    <strong>⏰ Important:</strong> This link will expire in 24 hours.
                </div>
                <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
            </div>
            <div class="footer">
                <p>This is an automated email from Claim Chaser by Maximized Revenue.</p>
                <p>Please do not reply to this email.</p>
                <p style="margin-top: 10px;">Email: claimchaser@maximizedrevenue.com</p>
            </div>
        </div>
    </body>
    </html>
    """

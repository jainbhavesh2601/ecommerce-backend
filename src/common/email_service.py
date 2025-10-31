import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from src.config import Config
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    def _create_smtp_connection():
        """Create and return an SMTP connection"""
        try:
            if Config.EMAIL_USE_TLS:
                server = smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(Config.EMAIL_HOST, Config.EMAIL_PORT)
            
            if Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD:
                server.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)
            
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {str(e)}")
            raise

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = Config.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Attach HTML version if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with EmailService._create_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    def send_verification_email(
        to_email: str,
        username: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification link to user
        
        Args:
            to_email: User's email address
            username: User's username
            verification_token: Verification token
            
        Returns:
            bool: True if email was sent successfully
        """
        verification_url = f"{Config.FRONTEND_URL}/verify-email?token={verification_token}"
        
        subject = "Verify Your Email - Artisans Alley"
        
        # Plain text version
        body = f"""
Hello {username},

Welcome to Artisans Alley! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account with us, please ignore this email.

Best regards,
Artisans Alley Team
        """.strip()
        
        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to Artisans Alley!</h2>
        <p>Hello {username},</p>
        <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{verification_url}" class="button">Verify Email Address</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #4CAF50;">{verification_url}</p>
        <p>This link will expire in 24 hours.</p>
        <div class="footer">
            <p>If you didn't create an account with us, please ignore this email.</p>
            <p>Best regards,<br>Artisans Alley Team</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return EmailService.send_email(to_email, subject, body, html_body)

    @staticmethod
    def send_welcome_email(to_email: str, username: str) -> bool:
        """
        Send welcome email after successful verification
        
        Args:
            to_email: User's email address
            username: User's username
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "Welcome to Artisans Alley!"
        
        body = f"""
Hello {username},

Your email has been successfully verified!

You can now access all features of Artisans Alley. Start exploring unique handcrafted items from talented artisans.

Thank you for joining our community!

Best regards,
Artisans Alley Team
        """.strip()
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to Artisans Alley!</h2>
        <p>Hello {username},</p>
        <p>Your email has been successfully verified! 🎉</p>
        <p>You can now access all features of Artisans Alley. Start exploring unique handcrafted items from talented artisans.</p>
        <p style="text-align: center;">
            <a href="{Config.FRONTEND_URL}" class="button">Start Shopping</a>
        </p>
        <p>Thank you for joining our community!</p>
        <p>Best regards,<br>Artisans Alley Team</p>
    </div>
</body>
</html>
        """.strip()
        
        return EmailService.send_email(to_email, subject, body, html_body)


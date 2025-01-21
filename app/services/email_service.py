from typing import List, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from pathlib import Path
import jinja2

class EmailService:
    def __init__(self):
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.EMAILS_FROM_EMAIL,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_FROM_NAME=settings.EMAILS_FROM_NAME,
            MAIL_STARTTLS=settings.SMTP_TLS,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates' / 'email'
        )
        self.fastmail = FastMail(self.conf)
        
        # Set up Jinja2 environment for email templates
        template_dir = Path(__file__).parent.parent / 'templates' / 'email'
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=True
        )
    
    async def send_email(
        self,
        email_to: str,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any]
    ) -> None:
        """Send an email using a template."""
        try:
            template = self.env.get_template(f"{template_name}.html")
            html_content = template.render(**template_data)
            
            message = MessageSchema(
                subject=subject,
                recipients=[email_to],
                body=html_content,
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise
    
    async def send_verification_email(self, email_to: str, token: str) -> None:
        """Send email verification link."""
        verification_url = f"{settings.SERVER_HOST}/verify-email?token={token}"
        await self.send_email(
            email_to=email_to,
            subject=f"{settings.PROJECT_NAME} - Verify your email",
            template_name="verification",
            template_data={
                "project_name": settings.PROJECT_NAME,
                "verification_url": verification_url
            }
        )
    
    async def send_password_reset_email(self, email_to: str, token: str) -> None:
        """Send password reset link."""
        reset_url = f"{settings.SERVER_HOST}/reset-password?token={token}"
        await self.send_email(
            email_to=email_to,
            subject=f"{settings.PROJECT_NAME} - Password reset",
            template_name="password_reset",
            template_data={
                "project_name": settings.PROJECT_NAME,
                "reset_url": reset_url
            }
        )
    
    async def send_2fa_disabled_notification(self, email_to: str) -> None:
        """Send notification when 2FA is disabled."""
        await self.send_email(
            email_to=email_to,
            subject=f"{settings.PROJECT_NAME} - Two-Factor Authentication Disabled",
            template_name="2fa_disabled",
            template_data={
                "project_name": settings.PROJECT_NAME
            }
        ) 
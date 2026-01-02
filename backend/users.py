# backend/users.py
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from db import User, get_user_db
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SECRET = os.getenv('JWT_SECRET', 'change_this_secret_key')

# 1. SETUP EMAIL CONFIGURATION
# Loaded from .env file
mail_conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv('MAIL_USERNAME', 'your_email@gmail.com'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD', 'your_app_password'),
    MAIL_FROM=os.getenv('MAIL_FROM', 'your_email@gmail.com'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
    MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    # 2. LOGIC TO SEND THE EMAIL
    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Token: {token}")

        # Construct the verification link (Point this to your Frontend URL)
        # Example: http://localhost:5173/verify?token=abc12345
        verify_link = f"http://localhost:5173/verify?token={token}"

        html_content = f"""
        <h1>Verify your Clark RAG Account</h1>
        <p>Click the link below to activate your account:</p>
        <a href="{verify_link}">Verify Email</a>
        """

        message = MessageSchema(
            subject="Clark RAG - Verify your Email",
            recipients=[user.email],
            body=html_content,
            subtype=MessageType.html
        )

        fm = FastMail(mail_conf)
        await fm.send_message(message)
        print("✅ Verification email sent successfully.")
async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

# JWT Configuration
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=14400)  # Tokens valid for 4 hours

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=BearerTransport(tokenUrl="auth/jwt/login"),
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
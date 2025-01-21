from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from cryptography.fernet import Fernet
import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from app.core.cache import cache_service
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    if len(password) < settings.MINIMUM_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {settings.MINIMUM_PASSWORD_LENGTH} characters long")
    return pwd_context.hash(password)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def check_rate_limit(key: str, limit: int = None, period: int = None) -> bool:
    """Check if the rate limit has been exceeded."""
    limit = limit or settings.RATE_LIMIT_REQUESTS
    period = period or settings.RATE_LIMIT_PERIOD
    
    try:
        current = await cache_service.get(f"rate_limit:{key}")
        if not current:
            await cache_service.set(f"rate_limit:{key}", 1, ttl=period)
            return True
        
        try:
            count = int(current)
        except (TypeError, ValueError):
            # Reset counter if value is corrupted
            await cache_service.set(f"rate_limit:{key}", 1, ttl=period)
            return True
            
        if count >= limit:
            return False
        
        await cache_service.set(f"rate_limit:{key}", count + 1, ttl=period)
        return True
    except Exception as e:
        logger.error(f"Rate limit error: {str(e)}")
        return True  # Default to allowing requests if Redis is unavailable

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

class Encryptor:
    def __init__(self):
        if not settings.ENCRYPTION_KEY:
            raise ValueError("Encryption key not set")
        
        # Generate a key from the settings key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"static_salt",  # In production, use a proper salt management strategy
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.ENCRYPTION_KEY.encode()))
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

async def track_login_attempts(user_id: int) -> bool:
    """Track failed login attempts and implement timeout."""
    key = f"login_attempts:{user_id}"
    try:
        attempts = await cache_service.get(key)
        if not attempts:
            await cache_service.set(key, 1, ttl=settings.LOGIN_ATTEMPT_TIMEOUT)
            return True
        
        count = int(attempts)
        if count >= settings.MAX_LOGIN_ATTEMPTS:
            return False
        
        await cache_service.set(key, count + 1, ttl=settings.LOGIN_ATTEMPT_TIMEOUT)
        return True
    except Exception:
        return True  # Default to allowing login if Redis is unavailable

def generate_verification_token() -> str:
    """Generate a token for email verification or password reset."""
    return secrets.token_urlsafe(32)

# Initialize the encryptor if encryption key is set
encryptor = None
if settings.ENCRYPTION_KEY:
    encryptor = Encryptor() 
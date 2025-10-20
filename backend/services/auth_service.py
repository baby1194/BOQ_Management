from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

from models import models
from schemas import schemas

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes

# HTTP Bearer token
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate a user by username and password"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()


async def get_current_user_from_cookie(request, db: Session) -> Optional[models.User]:
    """Get current user from HTTP cookie"""
    try:
        # Try to get token from cookie
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        username = verify_token(token)
        if username is None:
            return None
        
        user = get_user_by_username(db, username=username)
        return user
    except Exception:
        return None

def check_user_exists(db: Session) -> bool:
    """Check if any user exists in the system"""
    return db.query(models.User).first() is not None

def create_default_user(db: Session, username: str, password: str, system_password: str = "password") -> models.User:
    """Create the default/first user"""
    hashed_password = get_password_hash(password)
    hashed_system_password = get_password_hash(system_password)
    
    user = models.User(
        username=username,
        hashed_password=hashed_password,
        system_password=hashed_system_password,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

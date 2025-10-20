from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from database.database import get_db
from models import models
from schemas import schemas
from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_user_by_username,
    get_password_hash,
    verify_password,
    check_user_exists,
    create_default_user,
    get_current_user_from_cookie,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()
security = HTTPBearer()

@router.post("/signup", response_model=schemas.UserResponse)
async def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Sign up a new user (only allowed if no user exists)"""
    # Check if any user already exists
    if check_user_exists(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User already exists. Only one user is allowed in the system."
        )
    
    # Check if username already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    hashed_system_password = get_password_hash(user_data.system_password)
    
    db_user = models.User(
        username=user_data.username,
        hashed_password=hashed_password,
        system_password=hashed_system_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Return user without sensitive data
    return schemas.UserResponse(
        id=db_user.id,
        username=db_user.username,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )

@router.post("/signin", response_model=schemas.Token)
async def signin(user_credentials: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    """Sign in user and return access token"""
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signout")
async def signout(response: Response):
    """Sign out user by clearing the cookie"""
    response.delete_cookie("access_token")
    return {"message": "Successfully signed out"}

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user information"""
    user = await get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return schemas.UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.get("/check-auth")
async def check_auth_status(request: Request, db: Session = Depends(get_db)):
    """Check if user is authenticated (used by frontend)"""
    user = await get_current_user_from_cookie(request, db)
    if user:
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active
            }
        }
    return {"authenticated": False}

@router.get("/check-signup-allowed")
async def check_signup_allowed(db: Session = Depends(get_db)):
    """Check if signup is allowed (no user exists yet)"""
    return {"signup_allowed": not check_user_exists(db)}

@router.put("/profile", response_model=schemas.UserResponse)
async def update_profile(
    user_update: schemas.UserUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update user profile (password and system password)"""
    # Get current user from cookie
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    update_data = {}
    
    if user_update.password:
        update_data["hashed_password"] = get_password_hash(user_update.password)
    
    if user_update.system_password:
        update_data["system_password"] = get_password_hash(user_update.system_password)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update user
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return schemas.UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.post("/verify-system-password")
async def verify_system_password_endpoint(
    request_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify the system password for BOQ operations"""
    # Get current user from cookie
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    provided_password = request_data.get("system_password")
    if not provided_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System password is required"
        )
    
    # Verify the system password using the user's stored system_password hash
    try:
        is_valid = verify_password(provided_password, current_user.system_password)
        if is_valid:
            return {"verified": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid system password. Please check your system password in the profile page."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying system password"
        )

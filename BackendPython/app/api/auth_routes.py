# app/api/auth_routes.py
"""
Authentication routes for user registration, login, and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database_orm import get_db
from app.models.auth_schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse, AuthResponse, GoogleLoginRequest
)
from app.models.user_models import User
from app.services.auth_service import AuthService
from app.api.auth_middleware import get_current_user

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    
    - **email**: User email address (must be unique)
    - **password**: At least 6 characters
    - **full_name**: Optional full name
    - **phone**: Optional phone number
    """
    result = AuthService.register(db, user_data)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    user = result["user"]
    token = AuthService.generate_token(user.id, user.email)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login user and get access token
    
    - **email**: User email address
    - **password**: User password
    """
    result = AuthService.login(db, credentials.email, credentials.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"]
        )
    
    user = result["user"]
    token = result["token"]
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=AuthResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user (client should discard the token)
    """
    return AuthResponse(
        success=True,
        message="Logged out successfully"
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token
    """
    new_token = AuthService.generate_token(current_user.id, current_user.email)
    
    return TokenResponse(
        access_token=new_token,
        user=UserResponse.model_validate(current_user)
    )


@router.post("/google", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Login/Register user with Google OAuth token
    
    - **idToken**: Google ID token from frontend (@react-oauth/google)
    """
    result = AuthService.google_login(db, request.idToken)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"]
        )
    
    user = result["user"]
    token = result["token"]
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/verify-token", response_model=AuthResponse)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify if the token is valid
    """
    return AuthResponse(
        success=True,
        message="Token is valid",
        user=UserResponse.model_validate(current_user)
    )

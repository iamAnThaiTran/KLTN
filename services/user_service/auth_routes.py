"""
Auth routes for UserService with Google OAuth support
Handles user registration, login, Google OAuth, token management
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid
import logging
from main import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# Pydantic Models
# ============================================================================

from pydantic import BaseModel, EmailStr

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    idToken: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]

# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return pwd_context.verify(password, hashed_password)
    except:
        return False

def generate_token(user_id: str, email: str) -> Dict[str, Any]:
    """Generate JWT token"""
    expires = timedelta(hours=JWT_EXPIRATION_HOURS)
    expire = datetime.utcnow() + expires
    
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "access_token": token,
        "expires_in": int(expires.total_seconds()),
        "user_id": user_id,
        "email": email
    }

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ============================================================================
# Auth Routes
# ============================================================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password
    """
    try:
        # Import User model
        from main import User, UserPreference
        
        # Check if email already exists
        user_exists = db.query(User).filter(User.email == request.email).first()
        if user_exists:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate user ID
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Hash password
        hashed_password = hash_password(request.password)
        
        # Create user
        user = User(
            user_id=user_id,
            email=request.email,
            hashed_password=hashed_password,
            full_name=request.full_name or "",
            phone=request.phone or "",
            provider="local",
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.flush()
        
        # Create default preferences
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
        
        db.commit()
        
        # Generate token
        token_data = generate_token(user_id, request.email)
        
        user_response = {
            "user_id": user_id,
            "email": request.email,
            "full_name": request.full_name or "",
            "phone": ""
        }
        
        return {
            **token_data,
            "user": user_response,
            "token_type": "bearer",
            "message": "User registered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login user with email and password
    """
    try:
        from main import User
        
        # Check user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not user.hashed_password or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate token
        token_data = generate_token(user.user_id, user.email)
        
        user_response = {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name or "",
            "phone": user.phone or ""
        }
        
        return {
            **token_data,
            "user": user_response,
            "token_type": "bearer",
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/google")
async def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Login/Register user with Google OAuth token
    
    - **idToken**: Google ID token from frontend (@react-oauth/google)
    """
    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token
        from main import User, UserPreference
        
        # Get Google Client ID from environment
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not google_client_id:
            logger.error("GOOGLE_CLIENT_ID not configured in environment")
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        # Verify token
        request_obj = requests.Request()
        try:
            id_info = id_token.verify_oauth2_token(
                request.idToken, 
                request_obj, 
                audience=google_client_id
            )
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid Google token")
        
        # Extract info from token
        email = id_info.get('email')
        full_name = id_info.get('name', '')
        google_id = id_info.get('sub')
        
        if not email:
            raise HTTPException(status_code=400, detail="No email in Google token")
        
        # Check if user exists by oauth_id first (for returning users)
        user = db.query(User).filter(User.oauth_id == google_id).first()
        
        # If not found by oauth_id, check by email (for existing traditional users)
        if not user:
            user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user from Google info
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            try:
                user = User(
                    user_id=user_id,
                    email=email,
                    full_name=full_name,
                    hashed_password=None,  # NULL for OAuth users
                    provider="google",
                    provider_id=google_id,
                    oauth_provider='google',
                    oauth_id=google_id,
                    oauth_token=request.idToken,
                    is_verified=True,  # Verified since from Google
                    email_verified=True,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.flush()
                db.commit()
                
                # Create default preferences
                prefs = UserPreference(user_id=user_id)
                db.add(prefs)
                db.commit()
            except Exception as e:
                db.rollback()
                # User might exist from concurrent request, try to fetch again
                user = db.query(User).filter(User.oauth_id == google_id).first()
                if not user:
                    raise
        else:
            # Update OAuth info for existing user (in case switching to Google)
            if not user.oauth_id or user.oauth_id != google_id:
                user.oauth_provider = 'google'
                user.oauth_id = google_id
                user.oauth_token = request.idToken
                user.provider = 'google'
                user.provider_id = google_id
            # Update full name if empty
            if not user.full_name and full_name:
                user.full_name = full_name
            db.commit()
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate JWT token
        token_data = generate_token(user.user_id, user.email)
        
        # Build user response
        user_response = {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name or "",
            "phone": user.phone or "",
            "oauth_provider": user.oauth_provider
        }
        
        logger.info(f"User logged in with Google: {user.email}")
        
        return {
            **token_data,
            "user": user_response,
            "token_type": "bearer",
            "message": "Google login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Google login error: {e}")
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")


@router.get("/me")
async def get_current_user(authorization: str = Header(None)):
    """
    Get current authenticated user information
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return {
            "user_id": payload["user_id"],
            "email": payload["email"]
        }
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """
    Logout user (client should discard the token)
    """
    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(authorization: str = Header(None)):
    """
    Refresh access token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Generate new token
        new_token = generate_token(payload["user_id"], payload["email"])
        return {
            **new_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/verify-token")
async def verify_token_endpoint(authorization: str = Header(None)):
    """
    Verify if the token is valid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return {
            "success": True,
            "message": "Token is valid",
            "user_id": payload["user_id"],
            "email": payload["email"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

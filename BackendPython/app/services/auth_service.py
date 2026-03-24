# app/services/auth_service.py
"""
Authentication service for user registration, login, and token management
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user_models import User, UserPreferences
from app.models.auth_schemas import UserRegister, TokenPayload
from dotenv import load_dotenv

load_dotenv()

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            print(f"Password verification error: {e}")
            return False

    @staticmethod
    def generate_token(user_id: int, email: str, expires_in_hours: int = JWT_EXPIRATION_HOURS) -> str:
        """Generate JWT token"""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[TokenPayload]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token

    @staticmethod
    def register(db: Session, user_data: UserRegister) -> Dict[str, Any]:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                return {
                    "success": False,
                    "error": "Email already registered",
                    "user": None
                }

            # Create new user
            hashed_password = AuthService.hash_password(user_data.password)
            user = User(
                email=user_data.email,
                password_hash=hashed_password,
                full_name=user_data.full_name,
                phone=user_data.phone
            )
            
            db.add(user)
            db.flush()  # Flush to get the user ID but don't commit yet

            # Create default preferences for new user
            preferences = UserPreferences(
                user_id=user.id,
                preferred_categories=[],
                preferred_brands=[]
            )
            db.add(preferences)
            db.commit()  # Commit both user and preferences
            db.refresh(user)

            return {
                "success": True,
                "message": "User registered successfully",
                "user": user,
                "error": None
            }

        except IntegrityError as e:
            db.rollback()
            return {
                "success": False,
                "error": "Email already registered",
                "user": None
            }
        except Exception as e:
            db.rollback()
            print(f"Registration error: {e}")
            return {
                "success": False,
                "error": str(e),
                "user": None
            }

    @staticmethod
    def login(db: Session, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return token"""
        try:
            # Find user by email
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return {
                    "success": False,
                    "error": "Invalid email or password",
                    "user": None,
                    "token": None
                }

            # Verify password
            if not AuthService.verify_password(password, user.password_hash):
                return {
                    "success": False,
                    "error": "Invalid email or password",
                    "user": None,
                    "token": None
                }

            # Check if user is active
            if not user.is_active:
                return {
                    "success": False,
                    "error": "User account is inactive",
                    "user": None,
                    "token": None
                }

            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(user)

            # Generate token
            token = AuthService.generate_token(user.id, user.email)

            return {
                "success": True,
                "message": "Login successful",
                "user": user,
                "token": token,
                "error": None
            }

        except Exception as e:
            print(f"Login error: {e}")
            return {
                "success": False,
                "error": str(e),
                "user": None,
                "token": None
            }

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def google_login(db: Session, google_token: str) -> Dict[str, Any]:
        """Login/Register user with Google OAuth token"""
        try:
            from google.auth.transport import requests
            from google.oauth2 import id_token
            
            # Get Google Client ID from environment
            google_client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not google_client_id:
                raise ValueError("GOOGLE_CLIENT_ID not configured in environment")
            
            # Verify token
            request = requests.Request()
            id_info = id_token.verify_oauth2_token(
                google_token, 
                request, 
                audience=google_client_id
            )
            
            # Extract info from token
            email = id_info.get('email')
            full_name = id_info.get('name', '')
            google_id = id_info.get('sub')
            
            if not email:
                return {
                    "success": False,
                    "error": "No email in Google token",
                    "user": None,
                    "token": None
                }
            
            # Check if user exists by oauth_id first (for returning users)
            user = db.query(User).filter(User.oauth_id == google_id).first()
            
            # If not found by oauth_id, check by email (for existing traditional users)
            if not user:
                user = db.query(User).filter(User.email == email).first()
            
            if not user:
                # Create new user from Google info
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=None,  # NULL for OAuth users
                    oauth_provider='google',
                    oauth_id=google_id,
                    oauth_token=google_token,
                    is_verified=True,  # Verified since from Google
                    is_active=True
                )
                db.add(user)
                db.flush()
                
                # Create default preferences
                preferences = UserPreferences(
                    user_id=user.id,
                    preferred_categories=[],
                    preferred_brands=[]
                )
                db.add(preferences)
            else:
                # Update OAuth info for existing user (in case switching to Google)
                if not user.oauth_id or user.oauth_id != google_id:
                    user.oauth_provider = 'google'
                    user.oauth_id = google_id
                    user.oauth_token = google_token
                # Update full name if empty
                if not user.full_name and full_name:
                    user.full_name = full_name
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            # Generate JWT token
            jwt_token = AuthService.generate_token(user.id, user.email)
            
            return {
                "success": True,
                "message": "Google login successful",
                "user": user,
                "token": jwt_token,
                "error": None
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "user": None,
                "token": None
            }
        except Exception as e:
            print(f"Google login error: {e}")
            return {
                "success": False,
                "error": f"Google verification failed: {str(e)}",
                "user": None,
                "token": None
            }

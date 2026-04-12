# app/models/auth_schemas.py
"""
Pydantic schemas for authentication requests/responses
"""

from pydantic import BaseModel, EmailStr, Field, computed_field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserRegister(UserBase):
    """User registration schema"""
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
                "full_name": "John Doe",
                "phone": "+84912345678"
            }
        }


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123"
            }
        }


class UserResponse(UserBase):
    """User response schema"""
    id: int
    role: str
    is_verified: bool
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    @computed_field
    @property
    def name(self) -> str:
        """Alias for full_name, fallback to email username if not set"""
        return self.full_name or (self.email.split('@')[0] if self.email else 'User')

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthResponse(BaseModel):
    """Generic auth response"""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[UserResponse] = None


class TokenPayload(BaseModel):
    """JWT token payload"""
    user_id: int
    email: str
    exp: Optional[int] = None


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request"""
    idToken: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "idToken": "eye...nW5a"
            }
        }

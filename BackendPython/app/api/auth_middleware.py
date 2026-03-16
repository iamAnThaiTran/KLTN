# app/api/auth_middleware.py
"""
Authentication middleware for protecting routes
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional, Any
from app.services.auth_service import AuthService
from app.models.user_models import User
from app.config.database_orm import get_db

# Allow optional authentication - doesn't raise error if no credentials provided
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Any = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Verify token
    token_payload = AuthService.verify_token(token)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = AuthService.get_user_by_id(db, token_payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[Any] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns user if token is provided, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    token_payload = AuthService.verify_token(token)
    if not token_payload:
        return None
    
    user = AuthService.get_user_by_id(db, token_payload.user_id)
    if user and user.is_active:
        return user
    
    return None

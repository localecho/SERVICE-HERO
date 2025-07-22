#!/usr/bin/env python3
"""
SERVICE-HERO Authentication System
JWT-based authentication with secure password handling
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr


# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    """User registration model"""
    email: EmailStr
    password: str
    business_name: str
    business_type: str


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
    expires_in: int


class User(BaseModel):
    """User information"""
    email: str
    business_name: str
    business_type: str
    is_active: bool = True


class AuthManager:
    """Authentication manager"""
    
    def __init__(self):
        # In-memory user store (replace with database in production)
        self.users_db: Dict[str, Dict] = {}
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create new user account"""
        if user_data.email in self.users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = self.hash_password(user_data.password)
        
        # Store user
        self.users_db[user_data.email] = {
            "email": user_data.email,
            "hashed_password": hashed_password,
            "business_name": user_data.business_name,
            "business_type": user_data.business_type,
            "is_active": True,
            "created_at": datetime.now()
        }
        
        return User(
            email=user_data.email,
            business_name=user_data.business_name,
            business_type=user_data.business_type
        )
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user_data = self.users_db.get(email)
        if not user_data:
            return None
        
        if not self.verify_password(password, user_data["hashed_password"]):
            return None
        
        if not user_data["is_active"]:
            return None
        
        return User(
            email=user_data["email"],
            business_name=user_data["business_name"],
            business_type=user_data["business_type"],
            is_active=user_data["is_active"]
        )
    
    def create_access_token(self, user_email: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "sub": user_email,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            
            if email is None:
                return None
            
            user_data = self.users_db.get(email)
            if not user_data:
                return None
            
            return User(
                email=user_data["email"],
                business_name=user_data["business_name"],
                business_type=user_data["business_type"],
                is_active=user_data["is_active"]
            )
        
        except JWTError:
            return None
    
    def login(self, login_data: UserLogin) -> Token:
        """Login user and return token"""
        user = self.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            user_email=user.email,
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Global auth manager instance
auth_manager = AuthManager()

# Demo user for testing
demo_user = UserCreate(
    email="demo@servicehero.com",
    password="demo123",
    business_name="Demo Plumbing Co",
    business_type="plumbing"
)

auth_manager.create_user(demo_user)
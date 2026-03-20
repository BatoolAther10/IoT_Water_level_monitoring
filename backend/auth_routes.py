"""
Authentication Routes for IoT Water Tank Monitoring
Handles user registration, login, and token management
"""

import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:BAT@localhost:5432/iot-test"
)

print(f"[AUTH] Connecting to database: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"[AUTH] Database connection error: {e}")
    raise

Base = declarative_base()

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create tables
try:
    Base.metadata.create_all(bind=engine)
    print("[AUTH] Database tables created/verified")
except Exception as e:
    print(f"[AUTH] Error creating tables: {e}")

# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class UserRegister(BaseModel):
    """Registration request model"""
    email: str
    password: str


class UserLogin(BaseModel):
    """Login request model"""
    email: str
    password: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model"""
    token: str
    user: UserResponse


class VerifyTokenRequest(BaseModel):
    """Token verification request"""
    token: str


# ============================================================================
# AUTHENTICATION UTILITIES
# ============================================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"[AUTH] Password hashing error: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"[AUTH] Password verification error: {e}")
        return False


def create_access_token(user_id: int, email: str) -> str:
    """Create JWT access token"""
    try:
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        print(f"[AUTH] Token creation error: {e}")
        raise


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["authentication"])


# ============================================================================
# REGISTRATION ENDPOINT
# ============================================================================

@router.post("/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    
    Request:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Response:
    {
        "success": true,
        "message": "Registration successful",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "created_at": "2024-01-15T10:30:00"
        }
    }
    """
    
    print(f"[AUTH] Registration attempt for: {user_data.email}")
    
    try:
        # Validate email format
        if not user_data.email or "@" not in user_data.email:
            print(f"[AUTH] Invalid email format: {user_data.email}")
            return {
                "success": False,
                "detail": "Invalid email format"
            }
        
        # Validate password length
        if not user_data.password or len(user_data.password) < 6:
            print(f"[AUTH] Password too short")
            return {
                "success": False,
                "detail": "Password must be at least 6 characters"
            }
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        
        if existing_user:
            print(f"[AUTH] Email already registered: {user_data.email}")
            return {
                "success": False,
                "detail": "Email already registered"
            }
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create new user
        new_user = User(
            email=user_data.email,
            password_hash=password_hash
        )
        
        # Save to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"[AUTH] User registered successfully: {user_data.email}")
        
        return {
            "success": True,
            "message": "Registration successful. Please login.",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "created_at": new_user.created_at.isoformat()
            }
        }
    
    except Exception as e:
        db.rollback()
        print(f"[AUTH] Registration error: {e}")
        return {
            "success": False,
            "detail": f"Registration failed: {str(e)}"
        }


# ============================================================================
# LOGIN ENDPOINT
# ============================================================================

@router.post("/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    
    Request:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Response:
    {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "created_at": "2024-01-15T10:30:00"
        }
    }
    """
    
    print(f"[AUTH] Login attempt for: {user_data.email}")
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_data.email).first()
        
        if not user:
            print(f"[AUTH] User not found: {user_data.email}")
            return {
                "success": False,
                "detail": "Invalid email or password"
            }
        
        # Verify password
        if not verify_password(user_data.password, user.password_hash):
            print(f"[AUTH] Invalid password for: {user_data.email}")
            return {
                "success": False,
                "detail": "Invalid email or password"
            }
        
        # Create token
        token = create_access_token(user.id, user.email)
        
        print(f"[AUTH] User logged in successfully: {user_data.email}")
        
        return {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat()
            }
        }
    
    except Exception as e:
        print(f"[AUTH] Login error: {e}")
        return {
            "success": False,
            "detail": f"Login failed: {str(e)}"
        }


# ============================================================================
# VERIFY TOKEN ENDPOINT
# ============================================================================

@router.post("/verify-token")
async def verify_token(request: VerifyTokenRequest, db: Session = Depends(get_db)):
    """
    Verify JWT token validity
    
    Request:
    {
        "token": "eyJhbGciOiJIUzI1NiIs..."
    }
    
    Response:
    {
        "valid": true,
        "user_id": 1,
        "email": "user@example.com"
    }
    """
    
    try:
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            print(f"[AUTH] Token invalid: missing user_id or email")
            return {"valid": False}
        
        # Verify user exists in database
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            print(f"[AUTH] Token verified for: {email}")
            return {
                "valid": True,
                "user_id": user_id,
                "email": email
            }
        
        print(f"[AUTH] User not found for token: {email}")
        return {"valid": False}
    
    except jwt.ExpiredSignatureError:
        print(f"[AUTH] Token expired")
        return {"valid": False, "reason": "Token expired"}
    except jwt.InvalidTokenError as e:
        print(f"[AUTH] Invalid token: {e}")
        return {"valid": False, "reason": "Invalid token"}
    except Exception as e:
        print(f"[AUTH] Token verification error: {e}")
        return {"valid": False}


# ============================================================================
# GET ALL USERS (DEBUG ENDPOINT)
# ============================================================================

@router.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    """
    Get all registered users (DEBUG ONLY - Remove in production)
    """
    try:
        users = db.query(User).all()
        return {
            "total": len(users),
            "users": [
                {
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at.isoformat()
                }
                for user in users
            ]
        }
    except Exception as e:
        print(f"[AUTH] Error fetching users: {e}")
        return {"error": str(e)}


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/auth-health")
async def auth_health():
    """Check if authentication service is running"""
    return {
        "status": "healthy",
        "service": "authentication",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }
# backend/services/auth.py
"""
Authentication service for AI Doctor Scheduling System.
Handles user registration, login, token generation, and verification.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import jwt
import os
from functools import wraps
from flask import request, jsonify

from backend.models import User, UserRole
from backend.utils.db import get_session

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))


# ============================================================================
# Password Management
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    try:
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except ImportError:
        logger.error("bcrypt not installed. Install with: pip install bcrypt")
        raise Exception("Password hashing library not available")
    except Exception as e:
        logger.exception("Error hashing password")
        raise Exception(f"Password hashing failed: {str(e)}")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed_password: Hashed password to check against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ImportError:
        logger.error("bcrypt not installed")
        return False
    except Exception as e:
        logger.exception("Error verifying password")
        return False


# ============================================================================
# JWT Token Management
# ============================================================================

def create_access_token(user_id: int, email: str, role: str) -> Tuple[str, datetime]:
    """
    Create a JWT access token.
    
    Args:
        user_id: ID of the user
        email: Email of the user
        role: Role of the user
    
    Returns:
        Tuple of (token, expiry_datetime)
    """
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp())
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created for user {user_id}")
        
        return token, expiry
    except Exception as e:
        logger.exception("Error creating access token")
        raise Exception(f"Token creation failed: {str(e)}")


def create_refresh_token(user_id: int) -> Tuple[str, datetime]:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: ID of the user
    
    Returns:
        Tuple of (token, expiry_datetime)
    """
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp())
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Refresh token created for user {user_id}")
        
        return token, expiry
    except Exception as e:
        logger.exception("Error creating refresh token")
        raise Exception(f"Refresh token creation failed: {str(e)}")


def verify_token(token: str) -> Dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
    
    Returns:
        Decoded token payload
    
    Raises:
        Exception if token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise Exception("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise Exception("Invalid token")
    except Exception as e:
        logger.exception("Error verifying token")
        raise Exception(f"Token verification failed: {str(e)}")


# ============================================================================
# User Registration & Login
# ============================================================================

def register_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "patient",
    session=None
) -> Dict:
    """
    Register a new user.
    
    Args:
        email: User email (must be unique)
        password: User password (will be hashed)
        first_name: User's first name
        last_name: User's last name
        role: User role (patient, doctor, admin)
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with registration result
    """
    try:
        # Validate input
        if not email or "@" not in email:
            return {"success": False, "message": "Invalid email format"}
        if not password or len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters"}
        if not first_name or not last_name:
            return {"success": False, "message": "First and last name are required"}
        
        if session is None:
            with get_session() as session:
                return _register_user_with_session(email, password, first_name, last_name, role, session)
        else:
            return _register_user_with_session(email, password, first_name, last_name, role, session)
    
    except Exception as e:
        logger.exception("Registration error")
        return {"success": False, "message": "Registration failed"}


def _register_user_with_session(email, password, first_name, last_name, role, session):
    """Helper function to register user with provided session"""
    try:
        # Check if user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return {"success": False, "message": "Email already registered"}
        
        # Validate role
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            return {"success": False, "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user
        user = User(
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role=UserRole(role),
            is_active=True
        )
        
        session.add(user)
        session.commit()
        
        logger.info(f"User registered: {email}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email
        }
    except Exception as e:
        session.rollback()
        logger.exception("Error registering user")
        return {"success": False, "message": "Registration failed"}


def login_user(email: str, password: str, session=None) -> Dict:
    """
    Authenticate a user and return JWT tokens.
    
    Args:
        email: User email
        password: User password
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with login result and tokens
    """
    try:
        if not email or not password:
            return {"success": False, "message": "Email and password are required"}
        
        if session is None:
            with get_session() as session:
                return _login_user_with_session(email, password, session)
        else:
            return _login_user_with_session(email, password, session)
    
    except Exception as e:
        logger.exception("Login error")
        return {"success": False, "message": "Invalid email or password"}


def _login_user_with_session(email, password, session):
    """Helper function to login user with provided session"""
    try:
        # Find user
        user = session.query(User).filter_by(email=email).first()
        if not user:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return {"success": False, "message": "Invalid email or password"}
        
        # Check if user is active
        if not user.is_active:
            return {"success": False, "message": "User account is disabled"}
        
        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            return {"success": False, "message": "Invalid email or password"}
        
        # Generate tokens
        access_token, access_expiry = create_access_token(user.id, user.email, user.role.value)
        refresh_token, refresh_expiry = create_refresh_token(user.id)
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        session.commit()
        
        logger.info(f"User logged in: {email}")
        
        return {
            "success": True,
            "message": "Login successful",
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "access_token": access_token,
            "access_token_expiry": access_expiry.isoformat(),
            "refresh_token": refresh_token,
            "refresh_token_expiry": refresh_expiry.isoformat()
        }
    except Exception as e:
        logger.exception("Error during login")
        return {"success": False, "message": "Invalid email or password"}


def refresh_access_token(refresh_token: str, session=None) -> Dict:
    """
    Generate a new access token using a refresh token.
    
    Args:
        refresh_token: Valid refresh token
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with new access token
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            return {"success": False, "message": "Invalid token type"}
        
        user_id = payload.get("user_id")
        
        if session is None:
            with get_session() as session:
                return _refresh_access_token_with_session(user_id, session)
        else:
            return _refresh_access_token_with_session(user_id, session)
    
    except Exception as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        return {"success": False, "message": str(e)}


def _refresh_access_token_with_session(user_id, session):
    """Helper function to refresh access token with provided session"""
    try:
        # Get user
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Create new access token
        access_token, access_expiry = create_access_token(user.id, user.email, user.role.value)
        
        logger.info(f"Access token refreshed for user {user_id}")
        
        return {
            "success": True,
            "access_token": access_token,
            "access_token_expiry": access_expiry.isoformat()
        }
    except Exception as e:
        logger.exception("Error refreshing access token")
        return {"success": False, "message": "Token refresh failed"}


# ============================================================================
# Auth Middleware & Decorators
# ============================================================================

def require_auth(f):
    """
    Decorator to require authentication for a route.
    Verifies JWT token from Authorization header.
    
    Usage:
        @bp.route("/protected")
        @require_auth
        def protected_route():
            user = request.auth_user
            return jsonify({"message": f"Hello {user['email']}"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Missing authorization token"}), 401
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Verify token
            payload = verify_token(token)
            
            if payload.get("type") != "access":
                return jsonify({"success": False, "message": "Invalid token type"}), 401
            
            # Attach user info to request
            request.auth_user = payload
            
            return f(*args, **kwargs)
        
        except Exception as e:
            logger.warning(f"Auth error: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 401
    
    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator to require specific role for a route.
    Must be used after @require_auth.
    
    Usage:
        @bp.route("/admin-only")
        @require_auth
        @require_role("admin")
        def admin_route():
            return jsonify({"message": "Admin access granted"})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'auth_user'):
                return jsonify({"success": False, "message": "Not authenticated"}), 401
            
            user_role = request.auth_user.get("role")
            
            if user_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def get_current_user(session=None) -> Optional[Dict]:
    """
    Get the current authenticated user from the request context.
    
    Args:
        session: Optional SQLAlchemy session
    
    Returns:
        User dictionary if authenticated, None otherwise
    """
    if not hasattr(request, 'auth_user'):
        return None
    
    return request.auth_user
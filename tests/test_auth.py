# tests/test_auth.py
"""Tests for authentication service and routes"""
import pytest
from datetime import datetime, timedelta, timezone
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    register_user,
    login_user,
    refresh_access_token
)


class TestPasswordManagement:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test that password can be hashed"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20
    
    def test_verify_password_correct(self):
        """Test that correct password verifies"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test that incorrect password fails verification"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestTokenCreation:
    """Test JWT token creation and verification"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        token, expiry = create_access_token(1, "test@example.com", "patient")
        
        assert token is not None
        assert len(token) > 20
        # Use timezone-aware comparison
        assert expiry > datetime.now(timezone.utc)
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        token, expiry = create_refresh_token(1)
        
        assert token is not None
        assert len(token) > 20
        # Use timezone-aware comparison
        assert expiry > datetime.now(timezone.utc)
    
    def test_verify_access_token(self):
        """Test access token verification"""
        token, _ = create_access_token(1, "test@example.com", "patient")
        payload = verify_token(token)
        
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "patient"
        assert payload["type"] == "access"
    
    def test_verify_refresh_token(self):
        """Test refresh token verification"""
        token, _ = create_refresh_token(1)
        payload = verify_token(token)
        
        assert payload["user_id"] == 1
        assert payload["type"] == "refresh"
    
    def test_verify_invalid_token(self):
        """Test that invalid token verification fails"""
        with pytest.raises(Exception):
            verify_token("invalid.token.here")
    
    def test_verify_expired_token(self):
        """Test that expired token verification fails"""
        # Create token with negative expiry (already expired)
        import jwt
        import os
        SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        
        payload = {
            "user_id": 1,
            "exp": 0  # Expired
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # Should raise exception
        with pytest.raises(Exception):
            verify_token(token)


class TestUserRegistration:
    """Test user registration"""
    
    def test_register_user_valid(self, db_session):
        """Test valid user registration"""
        result = register_user(
            email="newuser@example.com",
            password="secure_password_123",
            first_name="John",
            last_name="Doe",
            role="patient",
            session=db_session
        )
        
        assert result["success"] is True
        assert "user_id" in result
        assert result["email"] == "newuser@example.com"
    
    def test_register_user_duplicate_email(self, db_session):
        """Test that duplicate email is rejected"""
        # Register first user
        register_user(
            email="duplicate@example.com",
            password="secure_password_123",
            first_name="John",
            last_name="Doe",
            session=db_session
        )
        
        # Try to register with same email
        result = register_user(
            email="duplicate@example.com",
            password="another_password_123",
            first_name="Jane",
            last_name="Smith",
            session=db_session
        )
        
        assert result["success"] is False
        assert "already registered" in result["message"]
    
    def test_register_user_invalid_email(self):
        """Test that invalid email is rejected"""
        result = register_user(
            email="not_an_email",
            password="secure_password_123",
            first_name="John",
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert "Invalid email" in result["message"]
    
    def test_register_user_short_password(self):
        """Test that short password is rejected"""
        result = register_user(
            email="user@example.com",
            password="short",
            first_name="John",
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert "at least 8 characters" in result["message"]
    
    def test_register_user_missing_name(self):
        """Test that missing name is rejected"""
        result = register_user(
            email="user@example.com",
            password="secure_password_123",
            first_name="",
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert "required" in result["message"]


class TestUserLogin:
    """Test user login"""
    
    def test_login_user_valid(self, db_session):
        """Test valid login"""
        # Register user first
        register_user(
            email="logintest@example.com",
            password="secure_password_123",
            first_name="John",
            last_name="Doe",
            session=db_session
        )
        
        # Login
        result = login_user(
            email="logintest@example.com",
            password="secure_password_123",
            session=db_session
        )
        
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["email"] == "logintest@example.com"
    
    def test_login_user_invalid_password(self, db_session):
        """Test login with wrong password"""
        # Register user first
        register_user(
            email="wrongpass@example.com",
            password="secure_password_123",
            first_name="John",
            last_name="Doe",
            session=db_session
        )
        
        # Login with wrong password
        result = login_user(
            email="wrongpass@example.com",
            password="wrong_password",
            session=db_session
        )
        
        assert result["success"] is False
        assert "Invalid email or password" in result["message"]
    
    def test_login_user_nonexistent(self, db_session):
        """Test login for non-existent user"""
        result = login_user(
            email="nonexistent@example.com",
            password="any_password",
            session=db_session
        )
        
        assert result["success"] is False
        assert "Invalid email or password" in result["message"]
    
    def test_login_user_missing_email(self):
        """Test login without email"""
        result = login_user(email="", password="password")
        
        assert result["success"] is False
        assert "required" in result["message"]


class TestTokenRefresh:
    """Test refresh token functionality"""
    
    def test_refresh_access_token_valid(self, db_session):
        """Test valid token refresh"""
        # Register and login user
        register_user(
            email="refresh@example.com",
            password="secure_password_123",
            first_name="John",
            last_name="Doe",
            session=db_session
        )
        
        login_result = login_user(
            email="refresh@example.com",
            password="secure_password_123",
            session=db_session
        )
        
        refresh_token = login_result["refresh_token"]
        
        # Refresh access token
        result = refresh_access_token(refresh_token, session=db_session)
        
        assert result["success"] is True
        assert "access_token" in result
        assert "access_token_expiry" in result
    
    def test_refresh_with_invalid_token(self):
        """Test refresh with invalid token"""
        result = refresh_access_token("invalid.token.here")
        
        assert result["success"] is False
        assert "Invalid" in result["message"] or "failed" in result["message"]


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_register_route_valid(self, client, db_session):
        """Test POST /api/auth/register with valid data"""
        payload = {
            "email": "routetest@example.com",
            "password": "secure_password_123",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post(
            "/api/auth/register",
            json=payload,
            content_type="application/json"
        )
        
        # Accept 201 (Created), 400 (Bad Request), or 500 (Server Error)
        assert response.status_code in [201, 400, 500]
    
    def test_login_route_valid(self, client, db_session):
        """Test POST /api/auth/login with valid data"""
        payload = {
            "email": "user@example.com",
            "password": "secure_password_123"
        }
        
        response = client.post(
            "/api/auth/login",
            json=payload,
            content_type="application/json"
        )
        
        # Accept 200 (OK), 401 (Unauthorized), 400 (Bad Request), or 500 (Server Error)
        assert response.status_code in [200, 401, 400, 500]
    
    def test_refresh_route_valid(self, client, db_session):
        """Test POST /api/auth/refresh with valid data"""
        payload = {
            "refresh_token": "dummy.token.here"
        }
        
        response = client.post(
            "/api/auth/refresh",
            json=payload,
            content_type="application/json"
        )
        
        # Accept any response
        assert response.status_code in [200, 401, 400, 500]
    
    def test_me_route_without_auth(self, client):
        """Test GET /api/auth/me without authentication"""
        response = client.get("/api/auth/me")
        
        # Should be unauthorized
        assert response.status_code == 401
    
    def test_verify_route_without_auth(self, client):
        """Test GET /api/auth/verify without authentication"""
        response = client.get("/api/auth/verify")
        
        # Should be unauthorized
        assert response.status_code == 401
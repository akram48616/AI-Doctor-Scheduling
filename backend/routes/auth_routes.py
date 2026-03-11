# backend/routes/auth_routes.py
"""
Authentication routes for user registration, login, and token management.
"""
import logging
from flask import Blueprint, jsonify, request
from backend.services.auth import (
    register_user,
    login_user,
    refresh_access_token,
    require_auth,
    get_current_user
)
from backend.utils.validators import sanitize_error_message

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    
    Request JSON:
    {
        "email": "user@example.com",
        "password": "secure_password_123",
        "first_name": "John",
        "last_name": "Doe",
        "role": "patient"  (optional, defaults to "patient")
    }
    
    Returns:
        JSON with registration result
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data provided"}), 400
        
        # Extract fields
        email = data.get("email")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        role = data.get("role", "patient")
        
        # Validate required fields
        if not all([email, password, first_name, last_name]):
            return jsonify({
                "success": False,
                "message": "Missing required fields: email, password, first_name, last_name"
            }), 400
        
        # Register user
        result = register_user(email, password, first_name, last_name, role)
        
        if result.get("success"):
            return jsonify(result), 201  # 201 Created
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.exception("Registration error")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/login", methods=["POST"])
def login():
    """
    Login a user and return JWT tokens.
    
    Request JSON:
    {
        "email": "user@example.com",
        "password": "secure_password_123"
    }
    
    Returns:
        JSON with access and refresh tokens
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data provided"}), 400
        
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400
        
        # Login user
        result = login_user(email, password)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 401  # Unauthorized
    
    except Exception as e:
        logger.exception("Login error")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh an access token using a refresh token.
    
    Request JSON:
    {
        "refresh_token": "your_refresh_token"
    }
    
    Returns:
        JSON with new access token
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data provided"}), 400
        
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return jsonify({
                "success": False,
                "message": "Refresh token is required"
            }), 400
        
        # Refresh token
        result = refresh_access_token(refresh_token)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 401
    
    except Exception as e:
        logger.exception("Token refresh error")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/me", methods=["GET"])
@require_auth
def get_me():
    """
    Get current authenticated user info.
    
    Requires: Authorization header with Bearer token
    
    Returns:
        JSON with current user information
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "Not authenticated"}), 401
        
        return jsonify({
            "success": True,
            "user": {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "role": user.get("role")
            }
        }), 200
    
    except Exception as e:
        logger.exception("Error getting current user")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/verify", methods=["GET"])
@require_auth
def verify():
    """
    Verify that an authentication token is valid.
    
    Requires: Authorization header with Bearer token
    
    Returns:
        JSON indicating token validity
    """
    try:
        user = get_current_user()
        return jsonify({
            "success": True,
            "message": "Token is valid",
            "user_id": user.get("user_id"),
            "email": user.get("email")
        }), 200
    
    except Exception as e:
        logger.exception("Error verifying token")
        return jsonify({"success": False, "message": str(e)}), 401
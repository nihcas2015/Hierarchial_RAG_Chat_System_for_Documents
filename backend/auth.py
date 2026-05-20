from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import LoginRequest, LoginResponse, SignupRequest, SignupResponse, ForgotPasswordRequest, ForgotPasswordResponse
from models import User
from database import get_db
from utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api", tags=["auth"])

# ===== SIGNUP ENDPOINT =====
@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new user account
    
    Request:
        - fullname: User's full name
        - email: User's email (must be unique)
        - password: Password (minimum 8 characters)
    
    Response:
        - success: True/False
        - message: Confirmation message
        - userId: New user ID (if successful)
    """
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = hash_password(request.password)
    
    # Create new user
    new_user = User(
        email=request.email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return SignupResponse(
        success=True,
        message="Account created successfully",
        userId=new_user.user_id
    )

# ===== LOGIN ENDPOINT =====
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login with email and password
    
    Request:
        - email: User's email
        - password: User's password
    
    Response:
        - success: True/False
        - token: JWT token (if successful)
        - userId: User ID
        - email: User's email
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create token
    token = create_access_token(user.user_id, user.email)
    
    return LoginResponse(
        success=True,
        message="Login successful",
        token=token,
        userId=user.user_id,
        email=user.email
    )

# ===== VERIFY TOKEN ENDPOINT =====
@router.get("/verify-token")
async def verify_token(token: str):
    """
    Verify if a JWT token is valid
    
    Query Params:
        - token: JWT token to verify
    
    Response:
        - success: True/False
        - valid: Is token valid
    """
    from utils import verify_token
    
    result = verify_token(token)
    
    if "error" in result:
        return {"success": False, "valid": False, "error": result["error"]}
    
    return {"success": True, "valid": True, "user_id": result.get("user_id")}

# ===== FORGOT PASSWORD ENDPOINT =====
@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset link
    
    Request:
        - email: User's email
    
    Response:
        - success: True/False
        - message: Confirmation message
    """
    
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal if email exists (security best practice)
        return ForgotPasswordResponse(
            success=True,
            message="If this email exists, a reset link will be sent"
        )
    
    # TODO: Send reset email with token
    # For now, just return success
    
    return ForgotPasswordResponse(
        success=True,
        message="If this email exists, a reset link will be sent"
    )

# ===== LOGOUT ENDPOINT =====
@router.post("/logout")
async def logout():
    """
    Logout user (frontend removes token from localStorage)
    
    Response:
        - success: True
        - message: Logout message
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }

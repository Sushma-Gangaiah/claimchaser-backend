from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from app.db.session import get_db
from app.middleware.auth import get_admin_user
from app.models import User, UserRole
from app.schemas.user import UserInvite, SetPasswordRequest, UserResponse
from app.utils.auth import create_invitation_token, hash_password
from app.utils.email import send_email, generate_invitation_email
from app.config import settings

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    invite_data: UserInvite,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Admin endpoint to invite a new user.
    Sends an email with a link to set up their password.
    """
    # Check if email already exists
    stmt = select(User).where(User.email == invite_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Generate invitation token
    invitation_token = create_invitation_token(invite_data.email)
    invitation_expires = datetime.utcnow() + timedelta(
        hours=settings.INVITATION_TOKEN_EXPIRATION_HOURS
    )

    # Create user with no password (pending setup)
    user = User(
        email=invite_data.email,
        full_name=invite_data.full_name,
        role=invite_data.role,
        invitation_token=invitation_token,
        invitation_expires=invitation_expires,
        password_set=False,
        is_active=False,  # Inactive until password is set
        created_by=current_admin.id
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send invitation email
    invitation_url = f"{settings.FRONTEND_URL}/set-password?token={invitation_token}"

    # Get admin name
    admin_name = current_admin.full_name

    html_content = generate_invitation_email(
        full_name=invite_data.full_name,
        invitation_url=invitation_url,
        inviter_name=admin_name
    )

    email_sent = await send_email(
        to_email=invite_data.email,
        subject=f"You're invited to join {settings.APP_NAME}",
        html_content=html_content
    )

    if not email_sent:
        # Log warning but don't fail the request
        print(f"Warning: Failed to send invitation email to {invite_data.email}")

    return user


@router.post("/set-password")
async def set_password(
    request: SetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    User endpoint to set password using invitation token.
    Activates the user account.
    """
    # Find user by invitation token
    stmt = select(User).where(User.invitation_token == request.token)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )

    # Check if token has expired
    if user.invitation_expires and user.invitation_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired"
        )

    # Check if password already set
    if user.password_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password has already been set for this account"
        )

    # Set password and activate user
    user.password_hash = hash_password(request.password)
    user.password_set = True
    user.is_active = True
    user.invitation_token = None  # Clear token after use
    user.invitation_expires = None

    await db.commit()

    return {
        "message": "Password set successfully. You can now log in.",
        "email": user.email
    }


@router.get("/verify-token/{token}")
async def verify_invitation_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify if an invitation token is valid.
    Used by frontend to check token before showing password form.
    """
    stmt = select(User).where(User.invitation_token == token)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )

    if user.invitation_expires and user.invitation_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired"
        )

    if user.password_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password has already been set for this account"
        )

    return {
        "valid": True,
        "email": user.email,
        "full_name": user.full_name,
        "expires_at": user.invitation_expires.isoformat() if user.invitation_expires else None
    }


@router.post("/resend/{user_id}", response_model=UserResponse)
async def resend_invitation(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_admin_user)
):
    """
    Admin endpoint to resend invitation to a user who hasn't set their password.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.password_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already set their password"
        )

    # Generate new invitation token
    invitation_token = create_invitation_token(user.email)
    invitation_expires = datetime.utcnow() + timedelta(
        hours=settings.INVITATION_TOKEN_EXPIRATION_HOURS
    )

    user.invitation_token = invitation_token
    user.invitation_expires = invitation_expires

    await db.commit()
    await db.refresh(user)

    # Send invitation email
    invitation_url = f"{settings.FRONTEND_URL}/set-password?token={invitation_token}"

    # Get admin name
    admin_name = current_admin.full_name

    html_content = generate_invitation_email(
        full_name=user.full_name,
        invitation_url=invitation_url,
        inviter_name=admin_name
    )

    email_sent = await send_email(
        to_email=user.email,
        subject=f"Reminder: Set up your {settings.APP_NAME} account",
        html_content=html_content
    )

    if not email_sent:
        print(f"Warning: Failed to send invitation email to {user.email}")

    return user

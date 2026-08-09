from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, cast, Date
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict
from app.db.session import get_db
from app.middleware.auth import get_admin_user
from app.models import User, Claim, Entry, UserRole, ClaimStatus, DropdownConfig, AdminDropdownConfig
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.claim import ClaimResponse
from app.schemas.entry import EntryResponse
from app.schemas.dropdown import DropdownConfigCreate, DropdownConfigUpdate, DropdownConfigResponse
from app.schemas.admin_config import AdminDropdownConfigCreate, AdminDropdownConfigUpdate, AdminDropdownConfigResponse
from app.utils.auth import hash_password
import pytz

router = APIRouter(prefix="/admin", tags=["admin"])

CST = pytz.timezone('America/Chicago')

def get_cst_now():
    """Get current time in CST timezone-naive format"""
    return datetime.now(CST).replace(tzinfo=None)


def get_entry_submitted_date_expr():
    """Use submitted_at for submitted-entry reporting, with created_at as legacy fallback."""
    return func.coalesce(Entry.submitted_at, Entry.created_at)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """List all users"""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.post("/users", response_model=UserResponse, deprecated=True)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Create a new user (Deprecated: Use /invitations/invite instead)
    This endpoint is kept for backward compatibility.
    """
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        password_set=True,
        created_by=current_admin.id
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Update user details"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_update.full_name:
        user.full_name = user_update.full_name
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.role:
        user.role = user_update.role

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Delete a user"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deleting themselves
    if str(user.id) == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await db.delete(user)
    await db.commit()

    return {"message": f"User {user.email} deleted successfully"}


@router.get("/claims", response_model=List[ClaimResponse])
async def list_all_claims(
    status: str = Query(None),
    account_number: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """List all claims with optional filters"""
    stmt = select(Claim)
    
    if status:
        try:
            claim_status = ClaimStatus(status)
            stmt = stmt.where(Claim.claim_status == claim_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if account_number:
        stmt = stmt.where(Claim.account_number.ilike(f"%{account_number}%"))
    
    stmt = stmt.order_by(Claim.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    claims = result.scalars().all()
    
    return claims


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get a specific claim"""
    stmt = select(Claim).where(Claim.id == claim_id)
    result = await db.execute(stmt)
    claim = result.scalars().first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    return claim


@router.get("/reports/claims-summary")
async def get_claims_summary(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get claims summary by status"""
    stmt = select(
        Claim.claim_status,
        Claim.payer_name,
        Claim.provider_name,
    ).order_by(Claim.claim_status)

    result = await db.execute(stmt)

    summary = {}
    for claim_status, payer, provider in result.fetchall():
        key = claim_status.value if claim_status else "unknown"
        if key not in summary:
            summary[key] = 0
        summary[key] += 1

    return summary


# ============================================
# USER ENTRIES MANAGEMENT
# ============================================

@router.get("/entries", response_model=List[EntryResponse])
async def get_all_user_entries(
    user_id: str = Query(None),
    is_draft: bool = Query(None),
    work_status: str = Query(None),
    date_from: Optional[str] = Query(None, description="Submitted start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Submitted end date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get all user entries with optional filters"""
    stmt = select(Entry)

    if user_id:
        stmt = stmt.where(Entry.user_id == user_id)

    if is_draft is not None:
        stmt = stmt.where(Entry.is_draft == is_draft)

    if work_status:
        stmt = stmt.where(Entry.work_status == work_status)

    submitted_date = get_entry_submitted_date_expr()
    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        stmt = stmt.where(cast(submitted_date, Date) >= start_date)

    if date_to:
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        stmt = stmt.where(cast(submitted_date, Date) <= end_date)

    stmt = stmt.order_by(get_entry_submitted_date_expr().desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    return entries


@router.get("/entries/summary")
async def get_entries_summary(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get summary of user entries"""
    stmt = select(Entry)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    total_entries = len(entries)
    draft_entries = sum(1 for e in entries if e.is_draft)
    submitted_entries = total_entries - draft_entries

    work_status_summary = {}
    for entry in entries:
        status = entry.work_status or "not_started"
        work_status_summary[status] = work_status_summary.get(status, 0) + 1

    return {
        "total_entries": total_entries,
        "draft_entries": draft_entries,
        "submitted_entries": submitted_entries,
        "work_status_summary": work_status_summary
    }


@router.get("/entries/daily-summary")
async def get_daily_summary(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get daily count of submitted entries per user within date range"""
    # Parse date params or default to last 7 days (CST)
    cst_today = get_cst_now().date()
    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        start_date = cst_today - timedelta(days=7)

    if date_to:
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        end_date = cst_today

    # Fetch submitted entries in date range
    submitted_date = get_entry_submitted_date_expr()
    stmt = select(Entry).where(
        Entry.is_draft == False,
        cast(submitted_date, Date) >= start_date,
        cast(submitted_date, Date) <= end_date
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # Group by user_name and date
    summary_map: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for entry in entries:
        user_name = entry.user_name or "Unknown"
        entry_date = (entry.submitted_at or entry.created_at).date().isoformat()
        summary_map[user_name][entry_date] += 1

    # Build date range list
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current.isoformat())
        current += timedelta(days=1)

    # Build response
    summary_rows = []
    for user_name in sorted(summary_map.keys()):
        row = {"user": user_name}
        total = 0
        for date_str in date_range:
            count = summary_map[user_name].get(date_str, 0)
            row[date_str] = count
            total += count
        row["total"] = total
        summary_rows.append(row)

    return {
        "date_range": date_range,
        "summary": summary_rows
    }


@router.get("/entries/client-summary")
async def get_client_summary(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get daily count of submitted entries per client code within date range"""
    # Parse date params or default to last 7 days (CST)
    cst_today = get_cst_now().date()
    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        start_date = cst_today - timedelta(days=7)

    if date_to:
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        end_date = cst_today

    # Fetch submitted entries in date range
    submitted_date = get_entry_submitted_date_expr()
    stmt = select(Entry).where(
        Entry.is_draft == False,
        cast(submitted_date, Date) >= start_date,
        cast(submitted_date, Date) <= end_date
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # Group by client_code and date
    summary_map: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    date_totals: Dict[str, int] = defaultdict(int)

    for entry in entries:
        client_code = entry.client_code or "Unknown"
        entry_date = (entry.submitted_at or entry.created_at).date().isoformat()
        summary_map[client_code][entry_date] += 1
        date_totals[entry_date] += 1

    # Build date range list
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current.isoformat())
        current += timedelta(days=1)

    # Build response rows
    summary_rows = []
    grand_total = 0
    for client_code in sorted(summary_map.keys()):
        row = {"client_code": client_code}
        row_total = 0
        for date_str in date_range:
            count = summary_map[client_code].get(date_str, 0)
            row[date_str] = count
            row_total += count
        row["total"] = row_total
        grand_total += row_total
        summary_rows.append(row)

    # Add total row
    total_row = {"client_code": "Total"}
    for date_str in date_range:
        total_row[date_str] = date_totals.get(date_str, 0)
    total_row["total"] = grand_total
    summary_rows.append(total_row)

    return {
        "date_range": date_range,
        "summary": summary_rows
    }


# ============================================
# DROPDOWN CONFIGURATIONS (CLIENT CODES & SOFTWARE)
# ============================================

@router.get("/dropdowns", response_model=List[DropdownConfigResponse])
async def get_all_dropdowns(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get all dropdown configurations"""
    stmt = select(DropdownConfig).order_by(DropdownConfig.field_key)
    result = await db.execute(stmt)
    dropdowns = result.scalars().all()
    return dropdowns


@router.get("/dropdowns/{field_key}", response_model=DropdownConfigResponse)
async def get_dropdown(
    field_key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get a specific dropdown configuration"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    return dropdown


@router.post("/dropdowns", response_model=DropdownConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_dropdown(
    dropdown_data: DropdownConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Create a new dropdown configuration"""
    # Check if field_key already exists
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == dropdown_data.field_key)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dropdown configuration '{dropdown_data.field_key}' already exists"
        )

    dropdown = DropdownConfig(
        field_key=dropdown_data.field_key,
        label=dropdown_data.label,
        options=dropdown_data.options,
        is_required=dropdown_data.is_required,
        created_by=current_admin.id
    )

    db.add(dropdown)
    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.patch("/dropdowns/{field_key}", response_model=DropdownConfigResponse)
async def update_dropdown(
    field_key: str,
    dropdown_data: DropdownConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Update a dropdown configuration"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    if dropdown_data.label is not None:
        dropdown.label = dropdown_data.label

    if dropdown_data.options is not None:
        dropdown.options = dropdown_data.options

    if dropdown_data.is_required is not None:
        dropdown.is_required = dropdown_data.is_required

    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.delete("/dropdowns/{field_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dropdown(
    field_key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Delete a dropdown configuration"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    await db.delete(dropdown)
    await db.commit()

    return None


@router.post("/dropdowns/{field_key}/options", response_model=DropdownConfigResponse)
async def add_dropdown_option(
    field_key: str,
    option_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Add a new option to a dropdown"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    if option_value in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option '{option_value}' already exists"
        )

    # Create a new list to ensure SQLAlchemy detects the change
    dropdown.options = dropdown.options + [option_value]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.put("/dropdowns/{field_key}/options/{option_value}", response_model=DropdownConfigResponse)
async def update_dropdown_option(
    field_key: str,
    option_value: str,
    new_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Update an option in a dropdown"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    if option_value not in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option '{option_value}' not found"
        )

    if new_value in dropdown.options and new_value != option_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option '{new_value}' already exists"
        )

    # Create a new list with the updated value
    dropdown.options = [new_value if opt == option_value else opt for opt in dropdown.options]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.delete("/dropdowns/{field_key}/options/{option_value}", response_model=DropdownConfigResponse)
async def remove_dropdown_option(
    field_key: str,
    option_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Remove an option from a dropdown"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dropdown configuration '{field_key}' not found"
        )

    if option_value not in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option '{option_value}' not found"
        )

    # Create a new list to ensure SQLAlchemy detects the change
    dropdown.options = [opt for opt in dropdown.options if opt != option_value]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


# ============================================
# ADMIN DROPDOWN CONFIGURATIONS
# (Insurance Type, Payer Type, Claim Type, Action Code, etc.)
# ============================================

@router.get("/admin-dropdowns", response_model=List[AdminDropdownConfigResponse])
async def get_all_admin_dropdowns(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get all admin dropdown configurations"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.is_active == True).order_by(AdminDropdownConfig.field_key)
    result = await db.execute(stmt)
    dropdowns = result.scalars().all()
    return dropdowns


@router.get("/admin-dropdowns/{field_key}", response_model=AdminDropdownConfigResponse)
async def get_admin_dropdown(
    field_key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Get a specific admin dropdown configuration"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    return dropdown


@router.post("/admin-dropdowns", response_model=AdminDropdownConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_dropdown(
    dropdown_data: AdminDropdownConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Create a new admin dropdown configuration"""
    # Check if field_key already exists
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == dropdown_data.field_key)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Admin dropdown configuration '{dropdown_data.field_key}' already exists"
        )

    dropdown = AdminDropdownConfig(
        field_key=dropdown_data.field_key,
        label=dropdown_data.label,
        description=dropdown_data.description,
        options=dropdown_data.options,
        is_active=dropdown_data.is_active,
        created_by=current_admin.id
    )

    db.add(dropdown)
    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.patch("/admin-dropdowns/{field_key}", response_model=AdminDropdownConfigResponse)
async def update_admin_dropdown(
    field_key: str,
    dropdown_data: AdminDropdownConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Update an admin dropdown configuration"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    if dropdown_data.label is not None:
        dropdown.label = dropdown_data.label

    if dropdown_data.description is not None:
        dropdown.description = dropdown_data.description

    if dropdown_data.options is not None:
        dropdown.options = dropdown_data.options

    if dropdown_data.is_active is not None:
        dropdown.is_active = dropdown_data.is_active

    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.delete("/admin-dropdowns/{field_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_dropdown(
    field_key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Delete an admin dropdown configuration"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    await db.delete(dropdown)
    await db.commit()

    return None


@router.post("/admin-dropdowns/{field_key}/options", response_model=AdminDropdownConfigResponse)
async def add_admin_dropdown_option(
    field_key: str,
    option_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Add a new option to an admin dropdown"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    if option_value in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option '{option_value}' already exists"
        )

    # Create a new list to ensure SQLAlchemy detects the change
    dropdown.options = dropdown.options + [option_value]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.put("/admin-dropdowns/{field_key}/options/{option_value}", response_model=AdminDropdownConfigResponse)
async def update_admin_dropdown_option(
    field_key: str,
    option_value: str,
    new_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Update an option in an admin dropdown"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    if option_value not in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option '{option_value}' not found"
        )

    if new_value in dropdown.options and new_value != option_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option '{new_value}' already exists"
        )

    # Create a new list with the updated value
    dropdown.options = [new_value if opt == option_value else opt for opt in dropdown.options]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown


@router.delete("/admin-dropdowns/{field_key}/options/{option_value}", response_model=AdminDropdownConfigResponse)
async def remove_admin_dropdown_option(
    field_key: str,
    option_value: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """Remove an option from an admin dropdown"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dropdown configuration '{field_key}' not found"
        )

    if option_value not in dropdown.options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option '{option_value}' not found"
        )

    # Create a new list to ensure SQLAlchemy detects the change
    dropdown.options = [opt for opt in dropdown.options if opt != option_value]
    dropdown.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(dropdown)

    return dropdown

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func, cast, Date
from typing import List, Dict
from datetime import datetime, date, timedelta
from app.db.session import get_db
from app.models import Entry, User, DropdownConfig, AdminDropdownConfig
from app.middleware.auth import get_current_user
from app.schemas.entry import EntryCreate, EntryUpdate, EntryResponse
import pytz

router = APIRouter(prefix="/user", tags=["user"])

CST = pytz.timezone('America/Chicago')

def get_cst_now():
    """Get current time in CST timezone-naive format"""
    return datetime.now(CST).replace(tzinfo=None)


@router.get("/entries", response_model=List[EntryResponse])
async def get_my_entries(
    drafts_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get entries for the current user. Use drafts_only=true to show drafts + today's submitted entries."""
    stmt = select(Entry).where(Entry.user_id == current_user.id)

    if drafts_only:
        # Show drafts OR entries submitted/updated today (CST date)
        cst_now = get_cst_now()
        today_cst = cst_now.date()
        stmt = stmt.where(
            or_(
                Entry.is_draft == True,
                cast(Entry.created_at, Date) == today_cst,
                cast(Entry.updated_at, Date) == today_cst
            )
        )

    stmt = stmt.order_by(Entry.created_at.desc())
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return entries


@router.post("/entries", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new entry"""
    import traceback
    try:
        from datetime import date as date_type

        print(f"Received entry data: {entry_data}")

        # Parse date fields if they're strings
        def parse_date_field(date_value):
            if not date_value:
                return None
            if isinstance(date_value, str):
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d').date()
                except ValueError:
                    return None
            return date_value

        date_of_service_value = parse_date_field(entry_data.date_of_service)
        last_submission_date_value = parse_date_field(entry_data.last_submission_date)
        follow_up_date_value = parse_date_field(entry_data.follow_up_date)
        date_worked_value = parse_date_field(entry_data.date_worked)

        # Use current time in CST for worked_date (always timezone-naive)
        worked_date_value = get_cst_now()

        # Set submitted_at only when not draft
        submitted_at_value = None if entry_data.is_draft else get_cst_now()

        print(f"Creating entry for user: {current_user.email}")

        # Convert empty strings to None for decimal fields
        charges_value = None
        if entry_data.charges and str(entry_data.charges).strip():
            charges_value = entry_data.charges

        paid_by_payer_value = None
        if entry_data.paid_by_payer and str(entry_data.paid_by_payer).strip():
            paid_by_payer_value = entry_data.paid_by_payer

        entry = Entry(
            user_id=current_user.id,
            user_name=entry_data.user_name or current_user.email.split('@')[0],
            client_code=entry_data.client_code,
            patient_name=entry_data.patient_name,
            date_of_service=date_of_service_value,
            provider_name=entry_data.provider_name,
            location=entry_data.location,
            payer_name=entry_data.payer_name,
            insurance_type=entry_data.insurance_type,
            insurance_payer_type=entry_data.insurance_payer_type,
            claim_type=entry_data.claim_type,
            charges=charges_value,
            paid_by_payer=paid_by_payer_value,
            payer_control_num=entry_data.payer_control_num,
            last_submission_date=last_submission_date_value,
            follow_up_date=follow_up_date_value,
            date_worked=date_worked_value,
            comments=entry_data.comments,
            status_code=entry_data.status_code or "Pending",
            sub_status_code=entry_data.sub_status_code,
            action_code=entry_data.action_code,
            work_status=entry_data.work_status or "not_started",
            software=entry_data.software,
            escalation=entry_data.escalation or False,
            is_draft=entry_data.is_draft,
            worked_date=worked_date_value,
            submitted_at=submitted_at_value
        )

        print("Entry object created, adding to DB...")
        db.add(entry)

        print("Committing to DB...")
        await db.commit()

        print("Refreshing entry...")
        await db.refresh(entry)

        print(f"Entry created successfully with ID: {entry.id}")
        return entry
    except Exception as e:
        print(f"ERROR creating entry: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entry: {str(e)}"
        )


@router.patch("/entries/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: str,
    entry_data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an entry (only allowed for draft entries)"""
    stmt = select(Entry).where(Entry.id == entry_id, Entry.user_id == current_user.id)
    result = await db.execute(stmt)
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )

    if not entry.is_draft:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit submitted entries"
        )

    update_data = entry_data.dict(exclude_unset=True)

    # Handle date field conversions - convert empty strings to None
    date_fields = ['date_of_service', 'last_submission_date', 'follow_up_date', 'date_worked']
    for date_field in date_fields:
        if date_field in update_data:
            if not update_data[date_field] or not str(update_data[date_field]).strip():
                update_data[date_field] = None
            elif isinstance(update_data[date_field], str):
                try:
                    update_data[date_field] = datetime.strptime(update_data[date_field], '%Y-%m-%d').date()
                except ValueError:
                    update_data[date_field] = None

    # Convert empty strings to None for decimal fields
    decimal_fields = ['charges', 'paid_by_payer']
    for decimal_field in decimal_fields:
        if decimal_field in update_data:
            if not update_data[decimal_field] or not str(update_data[decimal_field]).strip():
                update_data[decimal_field] = None

    # Convert empty strings to None for other optional string fields
    string_fields = [
        'client_code', 'patient_name', 'provider_name', 'location', 'payer_name',
        'insurance_type', 'insurance_payer_type', 'claim_type', 'payer_control_num',
        'comments', 'status_code', 'sub_status_code', 'action_code', 'software'
    ]
    for field in string_fields:
        if field in update_data and update_data[field] is not None and not str(update_data[field]).strip():
            update_data[field] = None

    for field, value in update_data.items():
        setattr(entry, field, value)

    # Set submitted_at when transitioning from draft to submitted
    if 'is_draft' in update_data and not update_data['is_draft'] and entry.submitted_at is None:
        entry.submitted_at = get_cst_now()

    entry.updated_at = get_cst_now()

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an entry (only allowed for draft entries)"""
    stmt = select(Entry).where(Entry.id == entry_id, Entry.user_id == current_user.id)
    result = await db.execute(stmt)
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )

    if not entry.is_draft:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete submitted entries"
        )

    await db.delete(entry)
    await db.commit()
    return None


@router.get("/dropdowns")
async def get_user_dropdowns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[str]]:
    """Get all dropdown options for user forms"""
    stmt = select(DropdownConfig)
    result = await db.execute(stmt)
    dropdowns = result.scalars().all()

    dropdown_dict = {}
    for dropdown in dropdowns:
        dropdown_dict[dropdown.field_key] = dropdown.options

    return dropdown_dict


@router.get("/dropdowns/{field_key}")
async def get_user_dropdown(
    field_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get specific dropdown options"""
    stmt = select(DropdownConfig).where(DropdownConfig.field_key == field_key)
    result = await db.execute(stmt)
    dropdown = result.scalars().first()

    if not dropdown:
        return []

    return dropdown.options


@router.get("/admin-dropdowns")
async def get_user_admin_dropdowns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[str]]:
    """Get all admin dropdown options for user forms"""
    stmt = select(AdminDropdownConfig).where(AdminDropdownConfig.is_active == True)
    result = await db.execute(stmt)
    dropdowns = result.scalars().all()

    dropdown_dict = {}
    for dropdown in dropdowns:
        dropdown_dict[dropdown.field_key] = dropdown.options

    return dropdown_dict

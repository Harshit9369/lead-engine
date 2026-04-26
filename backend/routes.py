"""
Lead Engine — API Routes
All endpoints for the frontend: auth, search, leads, scheduler.
"""
import logging
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, desc, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import User, ScheduledRole, Lead, ScanResult
from backend.scrapers.job_scraper import scrape_executive_jobs
from backend.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Pydantic Schemas ──────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    preferred_scan_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class SearchRequest(BaseModel):
    search_term: str = Field(default="", description="Role keyword (e.g., 'VP Engineering')")
    location: str = Field(default="", description="Location filter")
    industry: str = Field(default="", description="Industry filter")
    hours_old: int = Field(default=0, description="Max age in hours (0 = no limit)")
    results_wanted: int = Field(default=20, description="Number of results per source")


class AddRoleRequest(BaseModel):
    role_keyword: str = Field(..., description="Role to search, e.g. 'VP Engineering'")
    location: str = Field(default="", description="Location filter")
    industry: str = Field(default="", description="Industry filter")


class SaveLeadRequest(BaseModel):
    job_title: str
    company_name: str = ""
    company_url: str = ""
    job_url: str
    location: str = ""
    source: str = ""
    job_type: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: str = ""
    date_posted: str = ""
    company_industry: str = ""
    company_employees: str = ""
    score: int = 0
    outreach_tip: str = ""


class UpdateLeadRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


# ─── In-memory state for the current active search (per session) ─────
# Note: For production, this should be in Redis or per-request
_search_state = {
    "running": False,
    "results": [],
    "error": None,
    "query": "",
}


# ═══════════════════════════════════════════════════════════════════
#   AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"status": "success", "user": user.to_dict()}


@router.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT access token."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user.to_dict()


@router.patch("/api/auth/profile")
async def update_profile(
    user_up: UserUpdate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences (like scan time)."""
    if user_up.preferred_scan_time is not None:
        current_user.preferred_scan_time = user_up.preferred_scan_time
        await db.commit()
        # Trigger scheduler refresh if needed
        from backend.scheduler import refresh_user_job
        refresh_user_job(current_user)
        
    return current_user.to_dict()


# ═══════════════════════════════════════════════════════════════════
#   SEARCH ENDPOINTS (Publicly Accessible)
# ═══════════════════════════════════════════════════════════════════

async def _execute_search(request: SearchRequest):
    global _search_state
    _search_state = {"running": True, "results": [], "error": None, "query": request.search_term}
    try:
        leads = await asyncio.to_thread(
            scrape_executive_jobs,
            search_term=request.search_term,
            location=request.location,
            industry=request.industry,
            hours_old=request.hours_old if request.hours_old > 0 else None,
            results_wanted=request.results_wanted,
        )
        # Sort by date posted (newest first)
        leads.sort(key=lambda x: (x.get("date_posted", "") or ""), reverse=True)

        # Deduplicate by job_url
        unique_leads = []
        seen_urls = set()
        for lead in leads:
            url = lead.get("job_url")
            if url and url not in seen_urls:
                unique_leads.append(lead)
                seen_urls.add(url)

        _search_state["results"] = unique_leads
        _search_state["running"] = False
    except Exception as e:
        logger.error(f"[Search] error: {e}", exc_info=True)
        _search_state["error"] = str(e)
        _search_state["running"] = False


@router.post("/api/search")
async def trigger_search(request: SearchRequest, background_tasks: BackgroundTasks):
    """Trigger a search (Public)."""
    if _search_state.get("running"):
        return {"status": "busy", "message": "A search is already running."}
    background_tasks.add_task(_execute_search, request)
    return {"status": "started"}


@router.get("/api/search/status")
async def get_search_status():
    return {
        "running": _search_state.get("running", False),
        "results_count": len(_search_state.get("results", [])),
        "error": _search_state.get("error"),
    }


@router.get("/api/search/results")
async def get_search_results():
    if _search_state.get("running"): return {"status": "running"}
    return {"status": "complete", "leads": _search_state.get("results", [])}


# ═══════════════════════════════════════════════════════════════════
#   SAVED LEADS (Private to User)
# ═══════════════════════════════════════════════════════════════════

@router.post("/api/leads")
async def save_lead(
    req: SaveLeadRequest, 
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """Save a lead for the logged-in user."""
    # Check for existing lead for THIS user
    existing = await db.execute(
        select(Lead).where(Lead.user_id == user.id, Lead.job_url == req.job_url)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_saved"}

    lead = Lead(
        user_id=user.id,
        **req.model_dump()
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return {"status": "saved", "lead": lead.to_dict()}


@router.get("/api/leads")
async def list_leads(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List current user's leads."""
    query = select(Lead).where(Lead.user_id == user.id).order_by(desc(Lead.created_at))
    if status: query = query.where(Lead.status == status)
    result = await db.execute(query)
    return {"leads": [l.to_dict() for l in result.scalars().all()]}


@router.patch("/api/leads/{lead_id}")
async def update_lead(
    lead_id: int, 
    req: UpdateLeadRequest, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id))
    lead = result.scalar_one_or_none()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if req.status is not None: lead.status = req.status
    if req.notes is not None: lead.notes = req.notes
    await db.commit()
    return {"status": "updated"}


@router.delete("/api/leads/{lead_id}")
async def delete_lead(
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id))
    lead = result.scalar_one_or_none()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════
#   SCHEDULED ROLES (Private to User)
# ═══════════════════════════════════════════════════════════════════

@router.post("/api/scheduler/roles")
async def add_scheduled_role(
    req: AddRoleRequest, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    role = ScheduledRole(
        user_id=user.id,
        role_keyword=req.role_keyword.strip(),
        location=req.location.strip(),
        industry=req.industry.strip(),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"status": "added", "role": role.to_dict()}


@router.get("/api/scheduler/roles")
async def list_scheduled_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ScheduledRole).where(ScheduledRole.user_id == user.id).order_by(desc(ScheduledRole.created_at))
    )
    return {"roles": [r.to_dict() for r in result.scalars().all()]}


@router.delete("/api/scheduler/roles/{role_id}")
async def delete_scheduled_role(
    role_id: int, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(ScheduledRole).where(ScheduledRole.id == role_id, ScheduledRole.user_id == user.id))
    role = result.scalar_one_or_none()
    if not role: raise HTTPException(status_code=404, detail="Role not found")
    await db.delete(role)
    await db.commit()
    return {"status": "deleted"}


@router.get("/api/scheduler/results/grouped")
async def get_results_grouped(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    roles_result = await db.execute(
        select(ScheduledRole).where(ScheduledRole.user_id == user.id).order_by(ScheduledRole.created_at)
    )
    roles = roles_result.scalars().all()
    grouped = []
    for role in roles:
        res_q = await db.execute(
            select(ScanResult).where(ScanResult.role_id == role.id).order_by(desc(ScanResult.date_posted)).limit(50)
        )
        res_all = res_q.scalars().all()
        grouped.append({"role": role.to_dict(), "results": [r.to_dict() for r in res_all], "total": len(res_all)})
    return {"groups": grouped}


@router.get("/api/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    leads_count = await db.execute(select(func.count(Lead.id)).where(Lead.user_id == user.id))
    roles_count = await db.execute(select(func.count(ScheduledRole.id)).where(ScheduledRole.user_id == user.id))
    active_roles = await db.execute(
        select(func.count(ScheduledRole.id)).where(ScheduledRole.user_id == user.id, ScheduledRole.is_active == True)
    )
    return {
        "total_saved_leads": leads_count.scalar() or 0,
        "total_roles": roles_count.scalar() or 0,
        "active_roles": active_roles.scalar() or 0,
    }

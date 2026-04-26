"""
Lead Engine — Dynamic Scheduler
Handles per-user scan times stored in the User table.
All times are treated as IST.
"""
import logging
import asyncio
from datetime import date, datetime, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.database import async_session
from backend.models import User, ScheduledRole, ScanResult
from backend.scrapers.job_scraper import scrape_executive_jobs

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_scan_for_user(user_id: int):
    """Run all active scans for a specific user."""
    logger.info(f"[Scheduler] Starting scheduled scan for User {user_id}")
    
    async with async_session() as db:
        result = await db.execute(
            select(ScheduledRole).where(
                ScheduledRole.user_id == user_id, 
                ScheduledRole.is_active == True
            )
        )
        roles = result.scalars().all()

    if not roles:
        logger.info(f"[Scheduler] User {user_id} has no active roles")
        return

    for role in roles:
        try:
            logger.info(f"[Scheduler] Scanning '{role.role_keyword}' for User {user_id}")
            leads = await asyncio.to_thread(
                scrape_executive_jobs,
                search_term=role.role_keyword,
                location=role.location,
                industry=role.industry,
                hours_old=48, # Daily scan, 48h overlap is safe
                results_wanted=20
            )

            # Deduplicate incoming leads list
            unique_leads = []
            seen_urls = set()
            for l in leads:
                if l['job_url'] not in seen_urls:
                    unique_leads.append(l)
                    seen_urls.add(l['job_url'])

            if not unique_leads: continue

            async with async_session() as db:
                for lead_data in unique_leads:
                    # Dedup by job_url for this specific role
                    existing = await db.execute(
                        select(ScanResult).where(
                            ScanResult.role_id == role.id,
                            ScanResult.job_url == lead_data.get("job_url", "")
                        )
                    )
                    if existing.scalar_one_or_none(): continue

                    scan_result = ScanResult(
                        role_id=role.id,
                        job_title=lead_data.get("job_title", ""),
                        company_name=lead_data.get("company_name", ""),
                        company_url=lead_data.get("company_url", ""),
                        job_url=lead_data.get("job_url", ""),
                        location=lead_data.get("location", ""),
                        source=lead_data.get("source", ""),
                        description=lead_data.get("description", "")[:2000],
                        date_posted=lead_data.get("date_posted", ""),
                        company_industry=lead_data.get("company_industry", ""),
                        company_employees=lead_data.get("company_employees", ""),
                        scan_date=date.today(),
                    )
                    db.add(scan_result)
                await db.commit()
        except Exception as e:
            logger.error(f"[Scheduler] Error for role {role.id}: {e}")

    logger.info(f"[Scheduler] Complete for User {user_id}")


def refresh_user_job(user: User):
    """Reschedule or update a user's scan job."""
    job_id = f"user_scan_{user.id}"
    
    # Parse HH:MM from preferred_scan_time
    try:
        hour, minute = map(int, user.preferred_scan_time.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 10, 0  # Default to 10 AM IST

    # IST is UTC+5:30. To get 10 AM IST, we need 04:30 UTC
    # In a real setup, we'd handle timezone conversion properly
    # For now, let's assume the server environment or the scheduler is using IST
    # or just use a standard UTC offset logic.
    
    # Simplified: We treat the input as "local time" for the trigger
    # APScheduler can take a timezone object.
    trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Kolkata")

    if scheduler.get_job(job_id):
        scheduler.reschedule_job(job_id, trigger=trigger)
        logger.info(f"[Scheduler] Rescheduled job {job_id} to {user.preferred_scan_time} IST")
    else:
        scheduler.add_job(
            run_scan_for_user,
            trigger=trigger,
            args=[user.id],
            id=job_id,
            name=f"Daily Scan for User {user.id}",
            replace_existing=True,
        )
        logger.info(f"[Scheduler] Added new job {job_id} at {user.preferred_scan_time} IST")


async def init_scheduler():
    """Load all users on startup and schedule their scans."""
    logger.info("[Scheduler] Initializing per-user jobs...")
    
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

    for user in users:
        refresh_user_job(user)
    
    if not scheduler.running:
        scheduler.start()


def start_scheduler_service():
    """Wrapper to run init_scheduler in the event loop."""
    asyncio.create_task(init_scheduler())


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")

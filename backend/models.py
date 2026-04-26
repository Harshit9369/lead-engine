"""
Lead Engine — SQLAlchemy Models
Tables: ScheduledRole, Lead, ScanResult
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """User account for personalizing scans and leads."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    preferred_scan_time = Column(String(10), default="10:00")  # HH:MM in IST
    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("ScheduledRole", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "preferred_scan_time": self.preferred_scan_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScheduledRole(Base):
    """A role keyword the user wants scanned daily at their preferred time."""
    __tablename__ = "scheduled_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_keyword = Column(String(200), nullable=False)
    location = Column(String(200), default="")
    industry = Column(String(200), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="roles")
    scan_results = relationship("ScanResult", back_populates="role", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_keyword": self.role_keyword,
            "location": self.location,
            "industry": self.industry,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Lead(Base):
    """A lead the user explicitly saved/tracked from search results."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_title = Column(String(300), nullable=False)
    company_name = Column(String(300), default="")
    company_url = Column(String(500), default="")
    job_url = Column(String(500), nullable=False)
    location = Column(String(300), default="")
    source = Column(String(50), default="")
    job_type = Column(String(100), default="")
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    description = Column(Text, default="")
    date_posted = Column(String(50), default="")
    company_industry = Column(String(200), default="")
    company_employees = Column(String(100), default="")
    score = Column(Integer, default=0)
    outreach_tip = Column(Text, default="")
    status = Column(String(50), default="saved")  # saved | contacted | dismissed
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="leads")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "company_url": self.company_url,
            "job_url": self.job_url,
            "location": self.location,
            "source": self.source,
            "job_type": self.job_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "description": self.description,
            "date_posted": self.date_posted,
            "company_industry": self.company_industry,
            "company_employees": self.company_employees,
            "score": self.score,
            "outreach_tip": self.outreach_tip,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScanResult(Base):
    """Result from a scheduled daily scan — linked to a ScheduledRole."""
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("scheduled_roles.id"), nullable=False)
    job_title = Column(String(300), nullable=False)
    company_name = Column(String(300), default="")
    company_url = Column(String(500), default="")
    job_url = Column(String(500), nullable=False)
    location = Column(String(300), default="")
    source = Column(String(50), default="")
    description = Column(Text, default="")
    date_posted = Column(String(50), default="")
    company_industry = Column(String(200), default="")
    company_employees = Column(String(100), default="")
    score = Column(Integer, default=0)
    outreach_tip = Column(Text, default="")
    is_saved = Column(Boolean, default=False)
    scan_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("ScheduledRole", back_populates="scan_results")

    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "company_url": self.company_url,
            "job_url": self.job_url,
            "location": self.location,
            "source": self.source,
            "description": self.description,
            "date_posted": self.date_posted,
            "company_industry": self.company_industry,
            "company_employees": self.company_employees,
            "score": self.score,
            "outreach_tip": self.outreach_tip,
            "is_saved": self.is_saved,
            "scan_date": self.scan_date.isoformat() if self.scan_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

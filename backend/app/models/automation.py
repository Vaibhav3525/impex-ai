"""Durable campaign authorization, worker state and job history."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from app.core.database import Base

def now():
    return datetime.now(timezone.utc)

class AutomationPolicy(Base):
    __tablename__ = "automation_policies"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(String(64), unique=True, nullable=False)
    product_id = Column(String(64), nullable=False)
    countries = Column(JSON, nullable=False)
    daily_limit = Column(Integer, nullable=False, default=5)
    status = Column(String(20), nullable=False, default="Draft")
    product_snapshot = Column(String(64), nullable=True)
    authorized_by = Column(String(100), nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now, nullable=False)

class AutomationState(Base):
    __tablename__ = "automation_state"
    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=False, nullable=False)
    lease_owner = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    last_cycle_at = Column(DateTime, nullable=True)
    last_import_at = Column(DateTime, nullable=True)

class AutomationRun(Base):
    __tablename__ = "automation_runs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="Running", nullable=False)
    summary = Column(JSON, default=dict, nullable=False)
    error = Column(Text, nullable=True)

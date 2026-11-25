from datetime import timedelta
from types import SimpleNamespace
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import reviewer_identity
from app.models.automation import AutomationPolicy, AutomationState, AutomationRun
from app.models.outreach import OutreachCampaign
from app.models.product_profile import ProductProfile
from app.services.automation_service import utcnow, product_hash, policy_problem, run_cycle
from app.services.email_composer import compose_grounded_email

router = APIRouter(prefix="/automation", tags=["Automation"])

class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    product_id: str = Field(min_length=1)
    countries: list[str] = Field(min_length=1, max_length=30)
    daily_limit: int = Field(5, ge=1, le=50)

class Authorization(BaseModel):
    confirm: bool
    days: int = Field(30, ge=1, le=90)

class Switch(BaseModel):
    enabled: bool

def get_policy(db, policy_id):
    policy = db.get(AutomationPolicy, policy_id)
    if not policy:
        raise HTTPException(404, "Campaign not found.")
    return policy

def view(db, policy):
    campaign = db.query(OutreachCampaign).filter_by(campaign_id=policy.campaign_id).one()
    return {"id": policy.id, "name": campaign.name, "product_id": policy.product_id, "countries": policy.countries, "daily_limit": policy.daily_limit, "status": policy.status, "authorized_by": policy.authorized_by, "expires_at": policy.expires_at, "blocked_reason": policy_problem(db, policy)}

@router.get("/status")
def status(db: Session = Depends(get_db)):
    state = db.get(AutomationState, 1)
    runs = db.query(AutomationRun).order_by(AutomationRun.id.desc()).limit(20).all()
    return {"enabled": state.enabled, "heartbeat_at": state.heartbeat_at, "last_cycle_at": state.last_cycle_at, "sending_enabled": settings.OUTREACH_ENABLED, "feed_configured": bool(settings.BUYER_FEED_URL), "interval_seconds": settings.AUTOMATION_INTERVAL_SECONDS, "campaigns": [view(db, p) for p in db.query(AutomationPolicy).order_by(AutomationPolicy.id).all()], "runs": [{"id": r.id, "started_at": r.started_at, "finished_at": r.finished_at, "status": r.status, "summary": r.summary, "error": r.error} for r in runs]}

@router.post("/switch")
def switch(req: Switch, db: Session = Depends(get_db)):
    state = db.get(AutomationState, 1)
    state.enabled = req.enabled
    db.commit()
    return {"enabled": state.enabled}

@router.post("/campaigns", status_code=201)
def create_campaign(req: CampaignCreate, db: Session = Depends(get_db)):
    product = db.query(ProductProfile).filter_by(profile_id=req.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found.")
    countries = sorted({c.strip() for c in req.countries if c.strip()})
    if not countries:
        raise HTTPException(422, "Select at least one country.")
    if any(c.casefold() in {x.casefold() for x in product.excluded_countries or []} for c in countries):
        raise HTTPException(422, "Campaign countries include an excluded market.")
    campaign = OutreachCampaign(name=req.name, product_profile_id=req.product_id, status="Draft", daily_limit=req.daily_limit)
    db.add(campaign); db.flush()
    policy = AutomationPolicy(campaign_id=campaign.campaign_id, product_id=req.product_id, countries=countries, daily_limit=req.daily_limit)
    db.add(policy); db.commit()
    return view(db, policy)

@router.get("/campaigns/{policy_id}/preview")
def preview(policy_id: int, db: Session = Depends(get_db)):
    policy = get_policy(db, policy_id)
    product = db.query(ProductProfile).filter_by(profile_id=policy.product_id).first()
    if not product:
        raise HTTPException(409, "Product was removed.")
    sample = SimpleNamespace(company_name="{buyer company}", contact_name=None, country=policy.countries[0])
    return {"campaign": view(db, policy), "touches": [compose_grounded_email(sample, product, step, use_ai=False) for step in [1, 2, 3]], "requirements": "Verified low-risk buyer; current identity/import evidence; product match >=80; three touches maximum; four-day spacing; reply and suppression checks; campaign and installation rate limits."}

@router.post("/campaigns/{policy_id}/authorize")
def authorize(policy_id: int, req: Authorization, db: Session = Depends(get_db)):
    if not req.confirm:
        raise HTTPException(422, "Review all three message previews and explicitly authorize the campaign.")
    policy = get_policy(db, policy_id)
    product = db.query(ProductProfile).filter_by(profile_id=policy.product_id).first()
    if not product or not product.is_active or not product.export_readiness:
        raise HTTPException(409, "Review and activate the product first.")
    if not settings.EXPORTER_NAME.strip():
        raise HTTPException(409, "Configure your exporter identity before authorizing campaigns.")
    if any(c.casefold() in {x.casefold() for x in product.excluded_countries or []} for c in policy.countries):
        raise HTTPException(409, "Remove excluded markets by creating a revised campaign.")
    policy.product_snapshot = product_hash(product)
    policy.status, policy.authorized_by = "Active", reviewer_identity()
    policy.authorized_at, policy.expires_at = utcnow(), utcnow() + timedelta(days=req.days)
    db.commit()
    return view(db, policy)

@router.post("/campaigns/{policy_id}/pause")
def pause(policy_id: int, db: Session = Depends(get_db)):
    policy = get_policy(db, policy_id)
    policy.status = "Paused"
    db.commit()
    return view(db, policy)

@router.post("/run")
def run(db: Session = Depends(get_db)):
    return run_cycle(db, force=True)

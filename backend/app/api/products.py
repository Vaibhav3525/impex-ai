"""
Day 6 — Exporter Product Profiles & Buyer Matching API Router
Endpoints:
  POST   /api/v1/products                         — Create a new product configuration
  GET    /api/v1/products                         — List all exporter product profiles
  GET    /api/v1/products/{product_id}            — Get a specific product profile
  PUT    /api/v1/products/{product_id}            — Update product configuration
  DELETE /api/v1/products/{product_id}            — Delete product profile
  POST   /api/v1/products/{product_id}/match-leads — Match and rank all database leads
  POST   /api/v1/leads/{lead_id}/qualify/{product_id} — Qualify a single lead
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product_profile import ProductProfile
from app.models.lead import Lead
from app.schemas.product_profile import (
    ProductProfileCreate,
    ProductProfileUpdate,
    ProductProfileResponse,
    ProductMatchSummary,
    QualificationResult,
)
from app.services.qualification_service import (
    calculate_qualification_score,
    match_all_leads_for_product,
)

router = APIRouter(tags=["Product Profiles & Buyer Matching"])

def _get_product_or_404(db: Session, product_id: str) -> ProductProfile:
    """Helper to retrieve product by profile_id string or integer primary key."""
    if product_id.isdigit():
        prod = db.query(ProductProfile).filter(ProductProfile.id == int(product_id)).first()
    else:
        prod = db.query(ProductProfile).filter(ProductProfile.profile_id == product_id).first()
    
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product profile '{product_id}' not found.")
    return prod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Product Profile CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/products", response_model=ProductProfileResponse, status_code=status.HTTP_201_CREATED)
def create_product_profile(
    product_in: ProductProfileCreate,
    db: Session = Depends(get_db),
):
    """
    Creates an exporter product profile with specifications, HS codes,
    target countries, excluded markets, packaging, and payment terms.
    """
    new_product = ProductProfile(**product_in.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.get("/products", response_model=List[ProductProfileResponse])
def list_product_profiles(
    active_only: bool = Query(True, description="Filter for active product profiles only"),
    db: Session = Depends(get_db),
):
    """
    Lists all configured exporter product profiles.
    """
    query = db.query(ProductProfile)
    if active_only:
        query = query.filter(ProductProfile.is_active == True)
    return query.order_by(ProductProfile.created_at.desc()).all()


@router.get("/products/{product_id}", response_model=ProductProfileResponse)
def get_product_profile(
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full configuration of a specific product profile.
    """
    return _get_product_or_404(db, product_id)


@router.put("/products/{product_id}", response_model=ProductProfileResponse)
def update_product_profile(
    product_id: str,
    updates: ProductProfileUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates exporter specifications, target countries, or price thresholds.
    """
    prod = _get_product_or_404(db, product_id)
    update_data = updates.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(prod, key, value)
    
    db.commit()
    db.refresh(prod)
    return prod


@router.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
def delete_product_profile(
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    Deletes a product profile configuration.
    """
    prod = _get_product_or_404(db, product_id)
    db.delete(prod)
    db.commit()
    return {"message": f"Product profile '{product_id}' successfully removed.", "status": "deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Buyer Qualification & Matching
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/products/{product_id}/match-leads", response_model=ProductMatchSummary)
def match_leads_for_product_profile(
    product_id: str,
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum qualification score threshold"),
    include_disqualified: bool = Query(False, description="Include leads from excluded markets"),
    limit: int = Query(50, ge=1, le=200, description="Max number of candidate matches to return"),
    db: Session = Depends(get_db),
):
    """
    Evaluates all leads in the database against the product configuration.
    Ranks potential buyers by qualification score and returns structured explanations.
    """
    prod = _get_product_or_404(db, product_id)
    all_leads_count = db.query(Lead).count()

    matches = match_all_leads_for_product(
        db=db,
        product=prod,
        min_score=min_score,
        include_disqualified=include_disqualified,
        limit=limit,
    )

    qualified_count = len([m for m in matches if not m.is_disqualified and m.qualification_score >= 60.0])

    return ProductMatchSummary(
        product_profile=ProductProfileResponse.model_validate(prod),
        total_leads_evaluated=all_leads_count,
        qualified_leads_count=qualified_count,
        top_matches=matches,
    )


@router.post("/leads/{lead_id}/qualify/{product_id}", response_model=QualificationResult)
def qualify_single_lead_against_product(
    lead_id: str,
    product_id: str,
    db: Session = Depends(get_db),
):
    """
    Evaluates a specific buyer lead against an exporter product profile.
    Produces a 0-100 score, qualification tier, itemized breakdown, and audit explanation.
    """
    prod = _get_product_or_404(db, product_id)
    
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with id '{lead_id}' not found.")

    return calculate_qualification_score(lead, prod)

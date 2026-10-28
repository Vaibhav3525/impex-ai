from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class ProductProfileBase(BaseModel):
    product_name: str = Field(..., description="Name of export commodity, e.g. '1121 Basmati Rice'")
    product_category: str = Field(..., description="Industry category, e.g. 'Agricultural Commodities & Grains'")
    hs_code: Optional[str] = Field(None, description="6-to-8 digit HS Code, e.g. '10063020'")
    specifications: Optional[str] = Field(None, description="Technical specs, moisture content, grain length, etc.")
    grade: Optional[str] = Field(None, description="Product grade or sorting quality, e.g. 'Grade A Extra Long Grain'")
    origin_country: str = Field("India", description="Country of origin")
    
    available_quantity: Optional[str] = Field(None, description="Supply capacity e.g. '500 MT per month'")
    packaging: Optional[str] = Field(None, description="Packaging options e.g. '10kg / 25kg / 50kg Non-Woven Bags'")
    moq: Optional[str] = Field(None, description="Minimum order quantity e.g. '1x20ft Container (20 MT)'")
    target_price_min: Optional[float] = Field(None, description="Minimum target price in specified currency")
    target_price_max: Optional[float] = Field(None, description="Maximum target price in specified currency")
    currency: str = Field("USD", description="Currency code (USD, EUR, etc.)")
    incoterms: str = Field("FOB", description="Default Incoterms (FOB, CIF, CFR, etc.)")
    
    preferred_payment_terms: str = Field(
        "30% Advance + 70% against BL scan / Irrevocable LC at Sight",
        description="Standard payment security terms"
    )
    target_countries: List[str] = Field(default_factory=list, description="Priority buyer countries")
    excluded_countries: List[str] = Field(default_factory=list, description="Markets to exclude (embargo, sanctions, non-trade)")
    certifications: List[str] = Field(default_factory=list, description="Exporter certifications (APEDA, HACCP, ISO, etc.)")
    export_readiness: bool = Field(True, description="Whether export readiness audit is complete")
    is_active: bool = Field(True, description="Active status for buyer matching")

class ProductProfileCreate(ProductProfileBase):
    pass

class ProductProfileUpdate(BaseModel):
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    hs_code: Optional[str] = None
    specifications: Optional[str] = None
    grade: Optional[str] = None
    origin_country: Optional[str] = None
    available_quantity: Optional[str] = None
    packaging: Optional[str] = None
    moq: Optional[str] = None
    target_price_min: Optional[float] = None
    target_price_max: Optional[float] = None
    currency: Optional[str] = None
    incoterms: Optional[str] = None
    preferred_payment_terms: Optional[str] = None
    target_countries: Optional[List[str]] = None
    excluded_countries: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    export_readiness: Optional[bool] = None
    is_active: Optional[bool] = None

class ProductProfileResponse(ProductProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: str
    created_at: datetime
    updated_at: datetime

class QualificationBreakdown(BaseModel):
    product_relevance_score: float = Field(..., description="Product & category semantic match (Max 30)")
    country_alignment_score: float = Field(..., description="Target market match vs excluded list (Max 25)")
    import_evidence_score: float = Field(..., description="Verified import history / trade inquiry evidence (Max 20)")
    contact_quality_score: float = Field(..., description="Decision maker & corporate email presence (Max 15)")
    verification_readiness_score: float = Field(..., description="Lead verification standing (Max 10)")
    total_qualification_score: float = Field(..., description="Composite match score (0-100)")

class QualificationResult(BaseModel):
    lead_id: str
    company_name: str
    country: str
    product_profile_id: str
    product_name: str
    qualification_score: float = Field(..., description="Total qualification score 0-100")
    qualification_tier: str = Field(..., description="Highly Qualified | Conditionally Qualified | Marginally Qualified | Unqualified | Disqualified")
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    breakdown: QualificationBreakdown
    explanation: str = Field(..., description="Detailed factual explanation of qualification rationale")
    recommended_action: str = Field(..., description="Actionable next step for export sales team")
    qualified_at: datetime

class ProductMatchSummary(BaseModel):
    product_profile: ProductProfileResponse
    total_leads_evaluated: int
    qualified_leads_count: int
    top_matches: List[QualificationResult]

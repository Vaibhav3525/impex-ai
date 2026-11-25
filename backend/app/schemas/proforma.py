"""
Proforma Invoice & Export Quotation Schemas
DGFT / Customs compliant commercial contract quotation for international trade.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    hs_code: str = Field(pattern=r"^\d{6}(?:\d{2})?$")
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)
    unit_price: float = Field(gt=0, allow_inf_nan=False)
    total_amount: Optional[float] = Field(None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_total(self):
        from decimal import Decimal, ROUND_HALF_UP
        expected = (Decimal(str(self.quantity)) * Decimal(str(self.unit_price))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if self.total_amount is not None and Decimal(str(self.total_amount)).quantize(Decimal("0.01")) != expected:
            raise ValueError("Line total must equal quantity multiplied by unit price.")
        self.total_amount = float(expected)
        return self

class ProformaInvoiceCreate(BaseModel):
    deal_id: str = Field(min_length=1)
    validity_days: int = Field(30, ge=1, le=365)
    exporter_name: str = Field(min_length=3, max_length=255)
    exporter_address: str = Field(min_length=10)
    exporter_iec: str = Field(pattern=r"^[A-Za-z0-9]{10}$")
    exporter_gstin: str = Field(pattern=r"^[A-Za-z0-9]{15}$")
    exporter_ad_code: str = Field(min_length=7, max_length=14)
    bank_name: str = Field(min_length=3)
    bank_swift_code: str = Field(pattern=r"^[A-Z0-9]{8}(?:[A-Z0-9]{3})?$")
    bank_account_number: str = Field(min_length=8, max_length=50)
    country_of_origin: str = Field(min_length=2)
    port_of_loading: str = Field(min_length=3)
    destination_port: str = Field(min_length=3)
    incoterms: str = Field(pattern=r"^(FOB|CIF|CFR|EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS)$")
    payment_terms: str = Field(min_length=5)
    items: List[InvoiceItem] = Field(min_length=1, max_length=100)
    freight_insurance: float = Field(0.0, ge=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    notes: Optional[str] = None

    @model_validator(mode="after")
    def reject_template_details(self):
        if self.exporter_iec == "0319876543" or self.exporter_gstin == "27AABCB1234F1Z8" or self.bank_account_number == "CA-9876543210":
            raise ValueError("Replace template exporter and bank identifiers with your reviewed business details.")
        return self


class ProformaInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    deal_id: str
    lead_id: str
    issue_date: datetime
    validity_days: int

    # Exporter
    exporter_name: str
    exporter_address: str
    exporter_iec: Optional[str] = None
    exporter_gstin: Optional[str] = None
    exporter_ad_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_swift_code: Optional[str] = None
    bank_account_number: Optional[str] = None

    # Buyer
    buyer_company_name: str
    buyer_country: str
    buyer_address: Optional[str] = None
    buyer_contact: Optional[str] = None
    buyer_email: Optional[str] = None

    # Shipping
    country_of_origin: str
    port_of_loading: str
    destination_port: Optional[str] = None
    incoterms: str
    payment_terms: str

    # Financials
    items: List[Dict[str, Any]]
    subtotal: float
    freight_insurance: float
    total_amount: float
    currency: str

    notes: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


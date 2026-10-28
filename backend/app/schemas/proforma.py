"""
Proforma Invoice & Export Quotation Schemas
DGFT / Customs compliant commercial contract quotation for international trade.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class InvoiceItem(BaseModel):
    description: str = Field(..., description="Product description and specification grade")
    hs_code: Optional[str] = Field(None, description="6 or 8-digit Harmonized System code")
    quantity: float = Field(..., description="Commercial order volume")
    unit: str = Field("MT", description="Unit of measure (MT, KG, Bags, Cartons)")
    unit_price: float = Field(..., description="Price per unit in transaction currency")
    total_amount: float = Field(..., description="Line total amount")


class ProformaInvoiceCreate(BaseModel):
    deal_id: str = Field(..., description="Associated commercial export deal ID")
    validity_days: int = Field(30, description="Validity period in calendar days")
    
    # Exporter / Seller Details (Defaults to compliant Indian exporter template)
    exporter_name: str = Field("Bharat Agri-Exim Private Limited", description="Exporter company name")
    exporter_address: str = Field("Nariman Point, Mumbai - 400021, Maharashtra, India", description="Exporter registered address")
    exporter_iec: Optional[str] = Field("0319876543", description="10-digit DGFT Import Export Code")
    exporter_gstin: Optional[str] = Field("27AABCB1234F1Z8", description="GST Identification Number")
    exporter_ad_code: Optional[str] = Field("0210045", description="RBI Authorized Dealer Bank Code")
    bank_name: Optional[str] = Field("State Bank of India (Overseas Commercial Branch)", description="Bank name")
    bank_swift_code: Optional[str] = Field("SBININBB001", description="Bank SWIFT/BIC code")
    bank_account_number: Optional[str] = Field("CA-9876543210", description="Bank Account Number / IBAN")

    # Shipping Specifications
    country_of_origin: str = Field("India", description="Country of origin")
    port_of_loading: str = Field("Nhava Sheva (JNPT), Mumbai", description="Indian seaport/airport of departure")
    destination_port: Optional[str] = Field(None, description="Buyer's port of arrival")
    incoterms: str = Field("FOB", description="Incoterms 2020 (FOB, CIF, CFR, EXW)")
    payment_terms: Optional[str] = Field(None, description="Agreed payment terms (LC at Sight, 30% Advance, etc.)")

    # Line Items & Charges
    items: Optional[List[InvoiceItem]] = Field(None, description="Line item specifications")
    freight_insurance: float = Field(0.0, description="Freight and marine insurance charges if CIF/CFR")
    currency: str = Field("USD", description="Currency (USD, EUR, GBP, AED)")
    notes: Optional[str] = Field(None, description="Special commercial stipulations, packaging or inspection notes")


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

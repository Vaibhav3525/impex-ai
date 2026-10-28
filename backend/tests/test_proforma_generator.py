"""
Commercial Proforma Invoice & Export Quotation Generator Tests
Validates DGFT / Indian Customs export compliance, line-item pricing,
bank routing data, CRM pipeline auto-progression, and printable HTML output.
"""

import uuid
import pytest
from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.deal import Deal, ProformaInvoice
from app.schemas.proforma import ProformaInvoiceCreate, InvoiceItem
from app.services.proforma_service import generate_proforma_invoice, render_proforma_html
from app.api.pipeline import (
    create_deal_proforma_invoice,
    get_deal_proforma_invoice,
    get_deal_proforma_invoice_html,
    list_proforma_invoices
)


@pytest.fixture
def db_session():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_test_lead_and_deal(db, country="United Arab Emirates", product="Basmati Rice 1121", price=1150.0):
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-PI-{uid}",
        company_name=f"Gulf Trading Corp {uid}",
        country=country,
        city="Dubai",
        product_category=product,
        source="APEDA Directory",
        dedup_hash=f"hash_pi_{uid}",
        verification_status="Verified",
        business_email=f"procurement_{uid}@gulftrading.ae",
        pipeline_stage="Requirements Received"
    )
    db.add(lead)
    db.commit()

    deal = Deal(
        deal_id=f"DEAL-PI-{uid}",
        lead_id=lead.lead_id,
        product_name=product,
        hs_code="1006.30",
        required_quantity="50 MT",
        target_price=price,
        currency="USD",
        destination_port="Jebel Ali Port, Dubai",
        incoterms="FOB",
        payment_terms="30% Advance T/T + 70% against BL scan",
        stage="Requirements Received"
    )
    db.add(deal)
    db.commit()
    return lead, deal


def test_auto_generate_proforma_invoice_from_deal(db_session):
    """Proforma invoice automatically extracts items, calculates totals, and advances deal stage."""
    lead, deal = _make_test_lead_and_deal(db_session, price=1200.0)

    invoice = generate_proforma_invoice(db_session, deal, lead)

    assert invoice.invoice_number.startswith("PI-")
    assert invoice.deal_id == deal.deal_id
    assert invoice.lead_id == lead.lead_id
    assert invoice.buyer_company_name == lead.company_name
    assert invoice.buyer_country == "United Arab Emirates"
    assert invoice.subtotal == 60000.0  # 50 MT * $1,200.00
    assert invoice.total_amount == 60000.0
    assert invoice.currency == "USD"
    assert invoice.incoterms == "FOB"

    # Deal stage must automatically advance to Quotation Prepared
    db_session.refresh(deal)
    assert deal.stage == "Quotation Prepared"
    assert deal.quotation_amount == 60000.0
    assert f"#{invoice.invoice_number}" in deal.notes


def test_custom_line_items_and_cif_freight_calculation(db_session):
    """Custom multi-item proforma invoice accurately calculates subtotal and CIF freight."""
    lead, deal = _make_test_lead_and_deal(db_session, country="Germany")

    custom_req = ProformaInvoiceCreate(
        deal_id=deal.deal_id,
        incoterms="CIF",
        destination_port="Hamburg Port, Germany",
        payment_terms="100% Irrevocable LC at Sight",
        items=[
            InvoiceItem(
                description="Organic Black Pepper Extra Bold 550GL",
                hs_code="0904.11",
                quantity=10.0,
                unit="MT",
                unit_price=6500.0,
                total_amount=65000.0
            ),
            InvoiceItem(
                description="Alleppey Green Cardamom 8mm Grade",
                hs_code="0908.31",
                quantity=2.0,
                unit="MT",
                unit_price=22000.0,
                total_amount=44000.0
            )
        ],
        freight_insurance=3500.0,
        currency="USD",
        notes="Pre-shipment inspection certificate by SGS India required."
    )

    invoice = generate_proforma_invoice(db_session, deal, lead, custom_req)

    assert invoice.subtotal == 109000.0
    assert invoice.freight_insurance == 3500.0
    assert invoice.total_amount == 112500.0
    assert invoice.incoterms == "CIF"
    assert invoice.destination_port == "Hamburg Port, Germany"
    assert len(invoice.items) == 2


def test_render_proforma_html_statutory_compliance(db_session):
    """HTML rendered document contains all required Indian foreign trade statutory details."""
    lead, deal = _make_test_lead_and_deal(db_session)
    invoice = generate_proforma_invoice(db_session, deal, lead)

    html = render_proforma_html(invoice)

    # Check key DGFT and banking elements
    assert "PROFORMA INVOICE" in html
    assert invoice.invoice_number in html
    assert "IEC:" in html
    assert "GSTIN:" in html
    assert "AD Code:" in html
    assert "Country of Origin:</strong><br>India" in html
    assert "SWIFT / BIC Code:" in html
    assert "Foreign Trade (Development and Regulation) Act" in html
    assert "Accepted By (Buyer / Importer)" in html
    assert "Authorized Export Signatory" in html


def test_proforma_invoice_api_endpoints(db_session):
    """Test POST, GET and HTML API routes for Proforma Invoices."""
    lead, deal = _make_test_lead_and_deal(db_session)

    # 1. POST create PI
    res_create = create_deal_proforma_invoice(deal.deal_id, db=db_session)
    assert res_create.deal_id == deal.deal_id
    assert res_create.invoice_number.startswith("PI-")
    assert res_create.total_amount > 0

    # 2. GET invoice data
    res_get = get_deal_proforma_invoice(deal.deal_id, db=db_session)
    assert res_get.invoice_number == res_create.invoice_number
    assert res_get.buyer_company_name == lead.company_name

    # 3. GET invoice HTML response
    html_res = get_deal_proforma_invoice_html(deal.deal_id, db=db_session)
    assert html_res.status_code == 200
    assert res_create.invoice_number.encode() in html_res.body

    # 4. List all invoices
    invoices_list = list_proforma_invoices(db=db_session)
    assert len(invoices_list) > 0
    assert any(inv.invoice_number == res_create.invoice_number for inv in invoices_list)

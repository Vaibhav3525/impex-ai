"""
Proforma Invoice & Quotation Generation Service
DGFT / Customs compliant commercial document generator for Indian international trade.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.deal import Deal, ProformaInvoice
from app.schemas.proforma import ProformaInvoiceCreate, InvoiceItem


def _generate_invoice_no() -> str:
    now_year = datetime.now(timezone.utc).year
    return f"PI-{now_year}-{uuid.uuid4().hex[:6].upper()}"


def generate_proforma_invoice(
    db: Session,
    deal: Deal,
    lead: Lead,
    req: Optional[ProformaInvoiceCreate] = None
) -> ProformaInvoice:
    """
    Constructs a formal commercial export proforma invoice from a deal and lead record.
    Automatically calculates totals, persists the invoice, and updates CRM deal stage.
    """
    from fastapi import HTTPException
    from decimal import Decimal, ROUND_HALF_UP
    if req is None:
        raise HTTPException(422, "Exporter, bank, shipping and item details are required. No defaults are issued.")
    if req.deal_id != deal.deal_id:
        raise HTTPException(422, "Invoice deal_id must match the requested deal.")
    invoice_no = _generate_invoice_no()
    items_data = [item.model_dump() for item in req.items]
    subtotal_decimal = sum((Decimal(str(item["total_amount"])) for item in items_data), Decimal("0"))
    freight = req.freight_insurance
    subtotal = float(subtotal_decimal)
    grand_total = float((subtotal_decimal + Decimal(str(freight))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    currency = req.currency
    exporter_name, exporter_addr = req.exporter_name, req.exporter_address
    exporter_iec, exporter_gstin, exporter_ad_code = req.exporter_iec, req.exporter_gstin, req.exporter_ad_code
    bank_name, bank_swift, bank_acc = req.bank_name, req.bank_swift_code, req.bank_account_number
    incoterms, payment_terms = req.incoterms, req.payment_terms
    port_loading, dest_port = req.port_of_loading, req.destination_port

    invoice = ProformaInvoice(
        invoice_number=invoice_no,
        deal_id=deal.deal_id,
        lead_id=lead.lead_id,
        validity_days=req.validity_days if req else 30,
        exporter_name=exporter_name,
        exporter_address=exporter_addr,
        exporter_iec=exporter_iec,
        exporter_gstin=exporter_gstin,
        exporter_ad_code=exporter_ad_code,
        bank_name=bank_name,
        bank_swift_code=bank_swift,
        bank_account_number=bank_acc,
        buyer_company_name=lead.company_name,
        buyer_country=lead.country,
        buyer_address=lead.city or lead.country,
        buyer_contact=lead.contact_name,
        buyer_email=lead.business_email,
        country_of_origin=req.country_of_origin,
        port_of_loading=port_loading,
        destination_port=dest_port,
        incoterms=incoterms,
        payment_terms=payment_terms,
        items=items_data,
        subtotal=subtotal,
        freight_insurance=freight,
        total_amount=grand_total,
        currency=currency,
        notes=req.notes,
        status="Draft"
    )
    db.add(invoice)

    # 4. Advance Deal & Lead CRM Pipeline Stage
    prior_stage = deal.stage
    deal.quotation_amount = grand_total
    
    # Progress stage if earlier than Quotation Prepared
    earlier_stages = {
        "Discovered", "Verification Pending", "Verified Candidate", "Qualified",
        "Outreach Approved", "Email Sent", "Buyer Replied", "Requirements Received"
    }
    if deal.stage in earlier_stages:
        deal.stage = "Quotation Prepared"
    
    deal.updated_at = datetime.now(timezone.utc)
    log_msg = f"[Proforma Draft Created]: #{invoice_no} for {currency} {grand_total:,.2f} ({incoterms} {dest_port})"
    if deal.notes:
        deal.notes = f"{deal.notes}\n{log_msg}"
    else:
        deal.notes = log_msg

    # Also synchronize lead stage if applicable
    if lead.pipeline_stage in earlier_stages:
        lead.pipeline_stage = "Quotation Prepared"
        lead.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(invoice)
    db.refresh(deal)
    return invoice


def render_proforma_html(invoice: ProformaInvoice) -> str:
    """
    Renders a print-ready, professional HTML Proforma Invoice suitable for direct browser display or PDF export.
    """
    from html import escape
    from types import SimpleNamespace
    values = {column.name: getattr(invoice, column.name) for column in ProformaInvoice.__table__.columns}
    values = {key: escape(value) if isinstance(value, str) else value for key, value in values.items()}
    values["items"] = [{key: escape(value) if isinstance(value, str) else value for key, value in item.items()} for item in (invoice.items or [])]
    invoice = SimpleNamespace(**values)
    date_str = invoice.issue_date.strftime("%d-%b-%Y")
    
    line_rows = ""
    for idx, item in enumerate(invoice.items or []):
        line_num = idx + 1
        desc = item.get("description", "")
        hs = item.get("hs_code", "-")
        qty = item.get("quantity", 0)
        unit = item.get("unit", "MT")
        price = item.get("unit_price", 0.0)
        tot = item.get("total_amount", 0.0)
        line_rows += f"""
        <tr>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{line_num}</td>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">
            <strong>{desc}</strong>
            <div style="font-size: 11px; color: #64748b;">HS Code: {hs}</div>
          </td>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{qty} {unit}</td>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{invoice.currency} {price:,.2f}</td>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold;">{invoice.currency} {tot:,.2f}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DRAFT Proforma Invoice - {invoice.invoice_number}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 40px;
      color: #1e293b;
      background: #f8fafc;
      font-size: 13px;
      line-height: 1.5;
    }}
    .invoice-card {{
      max-width: 850px;
      margin: 0 auto;
      background: #ffffff;
      padding: 40px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      border-bottom: 2px solid #0f766e;
      padding-bottom: 20px;
      margin-bottom: 20px;
    }}
    .title {{
      font-size: 24px;
      font-weight: bold;
      color: #0f766e;
      letter-spacing: -0.5px;
    }}
    .meta-box {{
      text-align: right;
      font-size: 12px;
    }}
    .section-title {{
      font-size: 12px;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #0f766e;
      margin-bottom: 6px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 3px;
    }}
    .parties {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 25px;
      gap: 30px;
    }}
    .party-col {{
      flex: 1;
      background: #f8fafc;
      padding: 15px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
    }}
    .shipping-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      background: #f1f5f9;
      padding: 12px;
      border-radius: 6px;
      margin-bottom: 25px;
      font-size: 11px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 25px;
    }}
    th {{
      background: #0f766e;
      color: #ffffff;
      padding: 10px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .totals-area {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 25px;
    }}
    .banking-box {{
      flex: 1.5;
      background: #f8fafc;
      padding: 15px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
      font-size: 11px;
    }}
    .amounts-box {{
      flex: 1;
      text-align: right;
      padding-left: 30px;
    }}
    .grand-total {{
      font-size: 18px;
      font-weight: bold;
      color: #0f766e;
      border-top: 2px solid #0f766e;
      padding-top: 8px;
      margin-top: 8px;
    }}
    .footer-declaration {{
      border-top: 1px solid #cbd5e1;
      padding-top: 15px;
      font-size: 11px;
      color: #64748b;
      margin-top: 30px;
    }}
    .signature-row {{
      display: flex;
      justify-content: space-between;
      margin-top: 40px;
      padding-top: 20px;
    }}
    .signature-line {{
      border-top: 1px solid #94a3b8;
      width: 220px;
      text-align: center;
      padding-top: 6px;
      font-size: 11px;
    }}
    @media print {{
      body {{ background: #fff; margin: 0; }}
      .invoice-card {{ box-shadow: none; border: none; padding: 0; }}
    }}
  </style>
</head>
<body>
  <div class="invoice-card">
    <div class="header">
      <div>
        <div class="title">PROFORMA INVOICE</div>
        <div style="font-weight: bold; font-size: 16px; margin-top: 4px;">{invoice.exporter_name}</div>
        <div style="font-size: 11px; color: #64748b;">Merchant Exporter & Government Recognized Export House</div>
      </div>
      <div class="meta-box">
        <div><strong>Invoice No:</strong> {invoice.invoice_number}</div>
        <div><strong>Date:</strong> {date_str}</div>
        <div><strong>Validity:</strong> {invoice.validity_days} Days</div>
        <div><strong>Incoterms:</strong> {invoice.incoterms} 2020</div>
      </div>
    </div>

    <!-- Parties: Exporter & Buyer -->
    <div class="parties">
      <div class="party-col">
        <div class="section-title">Exporter (Seller)</div>
        <strong>{invoice.exporter_name}</strong><br>
        {invoice.exporter_address}<br>
        <strong>IEC:</strong> {invoice.exporter_iec or 'Applied'} | <strong>GSTIN:</strong> {invoice.exporter_gstin or '-'}<br>
        <strong>AD Code:</strong> {invoice.exporter_ad_code or '-'}
      </div>

      <div class="party-col">
        <div class="section-title">Consignee (Buyer)</div>
        <strong>{invoice.buyer_company_name}</strong><br>
        {invoice.buyer_address or invoice.buyer_country}<br>
        <strong>Attn:</strong> {invoice.buyer_contact or 'Procurement Officer'}<br>
        <strong>Email:</strong> {invoice.buyer_email or '-'}
      </div>
    </div>

    <!-- Shipping Specs -->
    <div class="shipping-grid">
      <div><strong>Country of Origin:</strong><br>{invoice.country_of_origin}</div>
      <div><strong>Port of Loading:</strong><br>{invoice.port_of_loading}</div>
      <div><strong>Port of Discharge:</strong><br>{invoice.destination_port or 'Any Named Safe Port'}</div>
      <div><strong>Payment Terms:</strong><br>{invoice.payment_terms}</div>
    </div>

    <!-- Commercial Items Table -->
    <table>
      <thead>
        <tr>
          <th style="width: 5%;">#</th>
          <th style="width: 45%; text-align: left;">Product Description & Specification</th>
          <th style="width: 15%; text-align: right;">Quantity</th>
          <th style="width: 15%; text-align: right;">Unit Rate</th>
          <th style="width: 20%; text-align: right;">Total Amount</th>
        </tr>
      </thead>
      <tbody>
        {line_rows}
      </tbody>
    </table>

    <!-- Financials & Banking -->
    <div class="totals-area">
      <div class="banking-box">
        <div class="section-title">Exporter Bank Routing Details</div>
        <div><strong>Bank Name:</strong> {invoice.bank_name or 'Not provided'}</div>
        <div><strong>SWIFT / BIC Code:</strong> {invoice.bank_swift_code or 'Not provided'}</div>
        <div><strong>Account / IBAN:</strong> {invoice.bank_account_number or 'Not provided'}</div>
        <div><strong>Beneficiary:</strong> {invoice.exporter_name}</div>
        <div style="margin-top: 6px; color: #64748b;"><em>Note: All overseas bank remittance charges on buyer's account.</em></div>
      </div>

      <div class="amounts-box">
        <div>Subtotal: <strong>{invoice.currency} {invoice.subtotal:,.2f}</strong></div>
        <div>Freight / Insurance: <strong>{invoice.currency} {invoice.freight_insurance:,.2f}</strong></div>
        <div class="grand-total">Total ({invoice.incoterms}): {invoice.currency} {invoice.total_amount:,.2f}</div>
      </div>
    </div>

    <div style="background: #f8fafc; padding: 10px 15px; border-radius: 6px; font-size: 11px; border: 1px solid #e2e8f0;">
      <strong>Special Terms & Conditions:</strong><br>
      {invoice.notes or 'Commercial draft. Review all exporter, bank, product and shipping details before use.'}
    </div>

    <!-- Statutory Declarations -->
    <div class="footer-declaration">
      <strong>Declaration:</strong> We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct according to the provisions of the Foreign Trade (Development and Regulation) Act and Indian Customs Regulations.
    </div>

    <div class="signature-row">
      <div class="signature-line">
        Accepted By (Buyer / Importer)<br>
        <span style="color: #94a3b8; font-size: 10px;">Authorized Signature & Company Stamp</span>
      </div>
      <div class="signature-line">
        For {invoice.exporter_name}<br>
        <span style="color: #94a3b8; font-size: 10px;">Authorized Export Signatory</span>
      </div>
    </div>
  </div>
</body>
</html>
"""
    return html


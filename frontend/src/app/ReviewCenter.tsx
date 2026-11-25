"use client";
import { useState } from "react";
import { api } from "@/lib/api";

type Props = { leads: any[]; products: any[]; onSaved: () => Promise<void> };
const inputClass = "mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 p-2 text-sm";
function Field({ label, value, onChange, required = true }: { label: string; value: string; onChange: (s: string) => void; required?: boolean }) {
  return <label className="block text-sm text-slate-300">{label}<input required={required} value={value} onChange={e => onChange(e.target.value)} className={inputClass} /></label>;
}

export default function ReviewCenter({ leads, products, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("Buyer evidence");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [leadId, setLeadId] = useState("");
  const [category, setCategory] = useState("identity");
  const [source, setSource] = useState("");
  const [reference, setReference] = useState("");
  const [finding, setFinding] = useState("");
  const [productId, setProductId] = useState("");
  const [product, setProduct] = useState<any>({});
  const [deals, setDeals] = useState<any[]>([]);
  const [dealId, setDealId] = useState("");
  const [paymentRef, setPaymentRef] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [invoice, setInvoice] = useState<Record<string, string>>({});
  const [invoiceLink, setInvoiceLink] = useState("");
  async function perform(action: () => Promise<any>) {
    setBusy(true); setMessage("");
    try { await action(); await onSaved(); setMessage("Saved. The workspace now reflects your review."); }
    catch (err: any) { setMessage(err.message || "Unable to save."); }
    finally { setBusy(false); }
  }
  async function show() {
    setOpen(true); setMessage("");
    try { setDeals(await api.getDeals()); } catch (err: any) { setMessage(err.message); }
  }
  return <><div className="mx-8 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-800 bg-amber-950/20 p-3 text-sm">
    <p className="text-amber-200">Imported buyers and product claims require evidence review before outreach.</p>
    <button onClick={show} className="rounded-lg bg-blue-600 px-4 py-2 font-semibold">Review records</button>
  </div>{open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-6"><section role="dialog" aria-modal="true" aria-label="Review records" className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-600 bg-slate-900 p-6">
    <div className="mb-5 flex items-center justify-between"><h2 className="text-xl font-bold">Review records</h2><button aria-label="Close review" onClick={() => setOpen(false)}>✕</button></div>
    <div className="mb-5 flex flex-wrap gap-2">{["Buyer evidence", "Product review", "Payment evidence", "Invoice draft"].map(t => <button key={t} onClick={() => { setTab(t); setMessage(""); }} className={`rounded-lg px-3 py-2 text-sm ${tab === t ? "bg-blue-600" : "bg-slate-800"}`}>{t}</button>)}</div>
    {message && <p role="status" className="mb-4 rounded-lg border border-slate-600 p-3 text-sm">{message}</p>}
    {tab === "Buyer evidence" && <form className="space-y-4" onSubmit={e => { e.preventDefault(); perform(() => api.recordEvidence(leadId, { category, source_url: source, document_reference: reference, finding })); }}>
      <p className="text-sm text-slate-400">Record what you personally checked, with a document reference and source. Scores reflect current reviewed evidence; profile text earns no points.</p>
      <label className="block text-sm">Buyer<select required className={inputClass} value={leadId} onChange={e => setLeadId(e.target.value)}><option value="">Select a buyer</option>{leads.map(l => <option key={l.lead_id} value={l.lead_id}>{l.company_name}</option>)}</select></label>
      <label className="block text-sm">Evidence category<select className={inputClass} value={category} onChange={e => setCategory(e.target.value)}>{["identity", "relevance", "website", "email", "imports", "independent"].map(c => <option key={c}>{c}</option>)}</select></label>
      <Field label="Source URL" value={source} onChange={setSource} />
      <Field label="Document / registry reference" value={reference} onChange={setReference} />
      <label className="block text-sm">Finding (at least 20 characters)<textarea required minLength={20} className={inputClass} value={finding} onChange={e => setFinding(e.target.value)} /></label>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50">Save reviewed evidence</button>
    </form>}
    {tab === "Product review" && <form className="space-y-4" onSubmit={e => { e.preventDefault(); perform(() => api.updateProduct(productId, { specifications: product.specifications, price_unit: product.price_unit || null, certifications: (product.certificationsText || "").split(",").map((x: string) => x.trim()).filter(Boolean), export_readiness: !!product.export_readiness })); }}>
      <p className="text-sm text-slate-400">Confirm the catalog facts against your own product and certification documents before marking a product ready.</p>
      <label className="block text-sm">Product<select required className={inputClass} value={productId} onChange={e => { setProductId(e.target.value); const p = products.find(x => x.profile_id === e.target.value); setProduct(p ? { ...p, certificationsText: (p.certifications || []).join(", ") } : {}); }}><option value="">Select a product</option>{products.map(p => <option key={p.profile_id} value={p.profile_id}>{p.product_name}</option>)}</select></label>
      <Field label="Specification" value={product.specifications || ""} onChange={v => setProduct({ ...product, specifications: v })} />
      <Field label="Price unit (MT, KG, Unit, etc.)" value={product.price_unit || ""} onChange={v => setProduct({ ...product, price_unit: v })} required={false} />
      <Field label="Certifications you have checked (comma-separated)" value={product.certificationsText || ""} onChange={v => setProduct({ ...product, certificationsText: v })} required={false} />
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={!!product.export_readiness} onChange={e => setProduct({ ...product, export_readiness: e.target.checked })} />I have reviewed the complete catalog record, including commercial terms, quantities, pricing and certifications.</label>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50">Save product review</button>
    </form>}
    {tab === "Payment evidence" && <form className="space-y-4" onSubmit={e => { e.preventDefault(); perform(() => api.verifyPayment(dealId, paymentRef, paymentNotes)); }}>
      <p className="text-sm text-slate-400">Only record funds or a credit instrument you have verified with the bank. Unsecured terms and unresolved buyer risks remain blocked.</p>
      <label className="block text-sm">Deal<select required className={inputClass} value={dealId} onChange={e => setDealId(e.target.value)}><option value="">Select a deal</option>{deals.map(d => <option key={d.deal_id} value={d.deal_id}>{d.deal_id} · {d.product_name} · {d.payment_terms}</option>)}</select></label>
      <Field label="Bank / payment document reference" value={paymentRef} onChange={setPaymentRef} />
      <label className="block text-sm">What you verified<textarea required minLength={20} value={paymentNotes} onChange={e => setPaymentNotes(e.target.value)} className={inputClass} /></label>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50">Record payment verification</button>
    </form>}
    {tab === "Invoice draft" && <form className="space-y-4" onSubmit={e => { e.preventDefault(); perform(async () => { await api.generateProformaInvoice(dealId, { ...invoice, deal_id: dealId, items: [{ description: invoice.description, hs_code: invoice.hs_code, quantity: Number(invoice.quantity), unit: invoice.unit, unit_price: Number(invoice.unit_price) }], freight_insurance: Number(invoice.freight_insurance || 0) }); setInvoiceLink(api.getProformaInvoiceHtmlUrl(dealId)); }); }}>
      <p className="text-sm text-slate-400">Enter your reviewed business details. The result is a commercial draft for review; it is not a compliance certification.</p>
      <label className="block text-sm">Deal<select required value={dealId} onChange={e => setDealId(e.target.value)} className={inputClass}><option value="">Select a deal</option>{deals.map(d => <option key={d.deal_id} value={d.deal_id}>{d.deal_id} · {d.product_name}</option>)}</select></label>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{Object.entries({ exporter_name: "Exporter legal name", exporter_address: "Exporter address", exporter_iec: "IEC", exporter_gstin: "GSTIN", exporter_ad_code: "Bank AD code", bank_name: "Bank name", bank_swift_code: "Bank SWIFT / BIC", bank_account_number: "Bank account / IBAN", country_of_origin: "Country of origin", port_of_loading: "Port of loading", destination_port: "Destination port", incoterms: "Incoterm (FOB, CIF, etc.)", payment_terms: "Payment terms", currency: "Currency (USD, EUR, etc.)", description: "Item description", hs_code: "HS code (6 or 8 digits)", quantity: "Quantity", unit: "Quantity unit", unit_price: "Price per unit", freight_insurance: "Freight / insurance" }).map(([key, label]) => <Field key={key} label={label} value={invoice[key] || ""} onChange={v => setInvoice({ ...invoice, [key]: v })} required={key !== "freight_insurance"} />)}</div>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50">Create invoice draft</button>
      {invoiceLink && <a href={invoiceLink} target="_blank" rel="noreferrer" className="ml-4 underline">Open draft</a>}
    </form>}
  </section></div>}</>;
}

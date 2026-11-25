"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
const input = "w-full rounded-lg border border-slate-600 bg-slate-950 p-2 text-sm";
export default function AutomationPanel({ products }: { products: any[] }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [product, setProduct] = useState("");
  const [countries, setCountries] = useState("");
  const [limit, setLimit] = useState(5);
  const [preview, setPreview] = useState<any>(null);
  const [reviewed, setReviewed] = useState(false);
  async function refresh() { try { setData(await api.automationStatus()); } catch (e: any) { setError(e.message); } }
  useEffect(() => { if (!open) return; refresh(); const timer = setInterval(refresh, 30000); return () => clearInterval(timer); }, [open]);
  async function act(fn: () => Promise<any>) { setBusy(true); setError(""); try { await fn(); await refresh(); } catch (e: any) { setError(e.message); } finally { setBusy(false); } }
  const lastBeat = data?.heartbeat_at ? Date.parse(data.heartbeat_at.endsWith("Z") || /[+-]\d\d:\d\d$/.test(data.heartbeat_at) ? data.heartbeat_at : data.heartbeat_at + "Z") : 0;
  const online = lastBeat && Date.now() - lastBeat < 120000;
  return <div className="mx-8 mt-3 rounded-xl border border-slate-700 bg-slate-900 p-3">
    <button onClick={() => setOpen(!open)} className="text-sm font-semibold text-blue-300">{open ? "Hide automation" : "Automation & campaigns"}</button>
    {open && <div className="mt-4 space-y-5">
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
      {data && <><div className="flex flex-wrap gap-3 text-sm"><span>Worker: {online ? "Online" : "Offline / no recent heartbeat"}</span><span>Automation: {data.enabled ? "Running" : "Paused"}</span><span>Email: {data.sending_enabled ? "Enabled" : "Disabled"}</span><span>Buyer feed: {data.feed_configured ? "Configured" : "Not connected"}</span></div>
        <p className="text-xs text-slate-400">Cycles run every {Math.round(data.interval_seconds / 60)} minutes. Campaigns use reviewed buyers and products, three touches maximum, four days apart. Replies, opt-outs and risk changes stop sending.</p>
        <div className="flex gap-3"><button disabled={busy} className="rounded bg-blue-600 px-3 py-2 text-sm disabled:opacity-50" onClick={() => act(() => api.automationSwitch(!data.enabled))}>{data.enabled ? "Pause all automation" : "Start automation"}</button><button disabled={busy || !data.enabled} className="rounded bg-slate-700 px-3 py-2 text-sm disabled:opacity-50" onClick={() => act(() => api.automationRun())}>Run a cycle now</button><button className="text-sm underline" onClick={refresh}>Refresh status</button></div>
        <form className="grid gap-3 rounded-lg border border-slate-700 p-4 md:grid-cols-2" onSubmit={e => { e.preventDefault(); act(async () => { await api.createCampaign({ name, product_id: product, countries: countries.split(",").map(c => c.trim()).filter(Boolean), daily_limit: limit }); setName(""); }); }}>
          <h3 className="font-semibold md:col-span-2">Create a campaign draft</h3>
          <label className="text-sm">Campaign name<input required minLength={3} value={name} onChange={e => setName(e.target.value)} className={input} /></label>
          <label className="text-sm">Product<select required value={product} onChange={e => setProduct(e.target.value)} className={input}><option value="">Choose product</option>{products.map(p => <option key={p.profile_id} value={p.profile_id}>{p.product_name}{p.export_readiness ? "" : " — review required"}</option>)}</select></label>
          <label className="text-sm">Countries (comma-separated)<input required value={countries} onChange={e => setCountries(e.target.value)} className={input} /></label>
          <label className="text-sm">Maximum messages per day<input required type="number" min={1} max={50} value={limit} onChange={e => setLimit(Number(e.target.value))} className={input} /></label>
          <button disabled={busy} className="rounded bg-slate-700 p-2 text-sm md:col-span-2">Create draft for review</button>
        </form>
        <div className="space-y-3">{data.campaigns.map((c: any) => <div key={c.id} className="rounded-lg border border-slate-700 p-3 text-sm"><div className="font-semibold">{c.name} · {c.status}</div><p>{c.countries.join(", ")} · {c.daily_limit} messages/day</p>{c.blocked_reason && <p className="text-amber-300">{c.blocked_reason}</p>}<div className="mt-2 flex gap-4"><button disabled={busy} className="underline" onClick={() => act(async () => { setPreview(await api.previewCampaign(c.id)); setReviewed(false); })}>Review messages & authorize</button>{c.status === "Active" && <button disabled={busy} className="text-rose-300 underline" onClick={() => act(() => api.pauseCampaign(c.id))}>Pause campaign</button>}</div></div>)}{data.campaigns.length === 0 && <p className="text-sm text-slate-400">No campaigns authorized. No automatic outreach can be sent.</p>}</div>
        {preview && <section className="space-y-3 rounded-lg border border-blue-600 p-4"><h3 className="font-bold">Authorize: {preview.campaign.name}</h3><p className="text-xs text-slate-400">{preview.requirements}</p>{preview.touches.map((t: any, i: number) => <details key={i}><summary className="cursor-pointer text-sm">Touch {i + 1}: {t.subject}</summary><pre className="whitespace-pre-wrap p-3 text-xs text-slate-300">{t.body_text}</pre></details>)}<label className="flex gap-2 text-sm"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed all three messages, this product, the countries and daily limit, and authorize this campaign for 30 days.</label><button disabled={busy || !reviewed} className="rounded bg-blue-600 px-3 py-2 text-sm disabled:opacity-50" onClick={() => act(async () => { await api.authorizeCampaign(preview.campaign.id); setPreview(null); })}>Authorize campaign</button><button className="ml-4 text-sm underline" onClick={() => setPreview(null)}>Close preview</button></section>}
        <section><h3 className="mb-2 font-semibold">Recent job runs</h3>{data.runs.length === 0 && <p className="text-sm text-slate-400">No cycles have run yet.</p>}{data.runs.map((r: any) => <details key={r.id} className="mb-2 rounded border border-slate-700 p-3"><summary className="cursor-pointer text-sm">Run #{r.id} · {r.status} · {r.started_at} · {r.summary.drafted || 0} drafted / {r.summary.sent || 0} sent</summary><p className="mt-2 text-xs">{r.summary.needs_review || 0} buyers need evidence review. Feed: {r.summary.feed?.status || "Not due"}</p>{r.error && <p className="text-sm text-rose-300">{r.error}</p>}{(r.summary.blocked_campaigns || []).map((b: any) => <p key={b.id} className="text-xs text-amber-300">Campaign #{b.id}: {b.reason}</p>)}</details>)}</section>
      </>}
    </div>}
  </div>;
}

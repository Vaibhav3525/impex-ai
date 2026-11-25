"use client";
import { useEffect, useState } from "react";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState("");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const base = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  useEffect(() => {
    fetch(`${base}/auth/session`, { credentials: "include" }).then(async res => {
      if (res.ok) setUser((await res.json()).username);
    }).catch(() => setError("The local server is unavailable.")).finally(() => setReady(true));
    const expired = () => { setUser(""); setError("Your session expired. Sign in again."); };
    window.addEventListener("impex-session-expired", expired);
    return () => window.removeEventListener("impex-session-expired", expired);
  }, [base]);
  async function signIn(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const res = await fetch(`${base}/auth/login`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Sign-in failed.");
      setPassword(""); setUser(data.username);
    } catch (err: any) { setError(err.message); } finally { setBusy(false); }
  }
  if (!ready) return <div className="p-12 text-slate-300">Checking your session…</div>;
  if (!user) return <main className="min-h-screen grid place-items-center bg-slate-950 px-6">
    <form onSubmit={signIn} className="w-full max-w-sm space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-8">
      <div><h1 className="text-2xl font-bold">IMPEX AI</h1><p className="mt-2 text-sm text-slate-400">Sign in to your buyer workspace.</p></div>
      <label className="block text-sm">Username<input autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 p-3" /></label>
      <label className="block text-sm">Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 p-3" /></label>
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
      <button disabled={busy} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50">{busy ? "Signing in…" : "Sign in"}</button>
      <p className="text-xs text-slate-400">Use the operator credentials configured for this installation.</p>
    </form>
  </main>;
  return <><button className="fixed bottom-3 left-4 z-50 rounded-lg bg-slate-800 px-3 py-2 text-xs text-slate-200" onClick={async () => {
    const res = await fetch(`${base}/auth/logout`, { method: "POST", credentials: "include", headers: { "X-Requested-With": "impex-ui" } });
    if (res.ok) setUser("");
  }}>Sign out · {user}</button>{children}</>;
}

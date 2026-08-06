"use client";

import { ArrowRight, BarChart3, LockKeyhole, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/auth";

const inputClass = "mt-2 w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/70 focus:ring-4 focus:ring-cyan-400/10";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(form: FormData) { setLoading(true); setError(""); const response = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) }); const result = await response.json(); if (!response.ok) { setError(result.detail ?? "Unable to sign in."); setLoading(false); return; } await fetch("/api/auth/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ accessToken: result.access_token }) }); router.push("/dashboard"); router.refresh(); }
  return <main className="grid min-h-screen bg-[#070b14] lg:grid-cols-[1.05fr_.95fr]">
    <section className="grid-noise relative hidden overflow-hidden border-r border-slate-800/80 p-12 lg:flex lg:flex-col lg:justify-between"><div className="absolute left-1/3 top-1/4 h-96 w-96 rounded-full bg-cyan-500/10 blur-[110px]" /><div className="relative flex items-center gap-3 font-semibold"><span className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-cyan-300"><Sparkles size={19} /></span>Sentinel <span className="-ml-2 text-cyan-300">AI</span></div><div className="relative max-w-xl"><p className="mb-5 text-xs font-semibold uppercase tracking-[.24em] text-cyan-300">Executive intelligence layer</p><h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.04em]">Know what changed.<br />Understand why.<br /><span className="text-slate-500">Act before others.</span></h1><p className="mt-6 max-w-lg text-lg leading-8 text-slate-400">A single command center for monitored signals, governed agents, and decision-ready insights.</p></div><div className="relative flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400"><BarChart3 className="text-cyan-300" size={20} /><span><strong className="text-white">Live intelligence</strong><br />Across every connected business function</span></div></section>
    <section className="flex items-center justify-center p-6 sm:p-10"><form action={submit} className="panel-glow w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/65 p-7 backdrop-blur-xl sm:p-10"><div className="mb-8"><div className="mb-6 flex items-center gap-2 text-xs font-medium text-emerald-300"><LockKeyhole size={15} /> Protected access</div><h2 className="text-3xl font-semibold tracking-tight">Welcome back</h2><p className="mt-2 text-sm leading-6 text-slate-400">Sign in to your intelligence command center.</p></div><div className="space-y-5"><label className="block text-sm font-medium text-slate-300">Work email<input required name="email" type="email" autoComplete="email" placeholder="you@company.com" className={inputClass} /></label><label className="block text-sm font-medium text-slate-300">Password<input required name="password" type="password" autoComplete="current-password" minLength={8} placeholder="Enter your password" className={inputClass} /></label></div>{error && <p role="alert" className="mt-5 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">{error}</p>}<Button disabled={loading} className="mt-7 h-12 w-full gap-2 rounded-xl font-semibold">{loading ? "Signing in..." : "Enter command center"}<ArrowRight size={17} /></Button><p className="mt-6 text-center text-sm text-slate-500">New to Sentinel? <Link className="font-medium text-cyan-300 hover:text-cyan-200" href="/register">Create an account</Link></p></form></section>
  </main>;
}

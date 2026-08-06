"use client";

import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/auth";

const inputClass = "mt-2 w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/70 focus:ring-4 focus:ring-cyan-400/10";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(form: FormData) {
    setError("");
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirmPassword") ?? "");
    if (password !== confirmPassword) { setError("Passwords do not match. Please confirm your password."); return; }
    setLoading(true);
    const response = await apiFetch("/auth/register", { method: "POST", body: JSON.stringify({ email: form.get("email"), full_name: form.get("fullName"), password }) });
    const result = await response.json();
    if (!response.ok) { setError(result.detail ?? "Unable to create account."); setLoading(false); return; }
    router.push("/login?registered=1");
  }

  return <main className="grid min-h-screen bg-[#070b14] lg:grid-cols-[1.05fr_.95fr]">
    <section className="grid-noise relative hidden overflow-hidden border-r border-slate-800/80 p-12 lg:flex lg:flex-col lg:justify-between">
      <div className="absolute left-1/3 top-1/4 h-96 w-96 rounded-full bg-cyan-500/10 blur-[110px]" />
      <Link href="/" className="relative flex items-center gap-3 font-semibold"><span className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-cyan-300"><Sparkles size={19} /></span><span>Sentinel <span className="text-cyan-300">AI</span></span></Link>
      <div className="relative max-w-xl"><p className="mb-5 text-xs font-semibold uppercase tracking-[.24em] text-cyan-300">Intelligence, operationalized</p><h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.04em]">Turn business signals into decisions your team can defend.</h1><p className="mt-6 max-w-lg text-lg leading-8 text-slate-400">Deploy governed AI agents across your data estate and give every leader a trusted, real-time view of what matters.</p></div>
      <div className="relative grid grid-cols-3 gap-4 text-sm">{[["SOC-ready", "Controls"], ["24/7", "Monitoring"], ["100%", "Auditable"]].map(([value, label]) => <div key={label} className="border-l border-slate-700 pl-4"><p className="font-semibold text-white">{value}</p><p className="mt-1 text-slate-500">{label}</p></div>)}</div>
    </section>
    <section className="flex items-center justify-center p-6 sm:p-10"><form action={submit} className="panel-glow w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900/65 p-7 backdrop-blur-xl sm:p-10">
      <div className="mb-8"><div className="mb-6 flex items-center gap-2 text-xs font-medium text-emerald-300"><ShieldCheck size={15} /> Secure enterprise workspace</div><h2 className="text-3xl font-semibold tracking-tight">Create your workspace</h2><p className="mt-2 text-sm leading-6 text-slate-400">Start building a shared intelligence layer for your business.</p></div>
      <div className="grid gap-5 sm:grid-cols-2"><label className="text-sm font-medium text-slate-300 sm:col-span-2">Full name<input required name="fullName" autoComplete="name" placeholder="Nishant Sharma" className={inputClass} /></label><label className="text-sm font-medium text-slate-300 sm:col-span-2">Work email<input required name="email" type="email" autoComplete="email" placeholder="you@company.com" className={inputClass} /></label><label className="text-sm font-medium text-slate-300">Password<input required name="password" type="password" autoComplete="new-password" minLength={8} placeholder="Minimum 8 characters" className={inputClass} /></label><label className="text-sm font-medium text-slate-300">Confirm password<input required name="confirmPassword" type="password" autoComplete="new-password" minLength={8} placeholder="Repeat password" className={inputClass} /></label></div>
      <div className="mt-4 flex items-center gap-2 text-xs text-slate-500"><CheckCircle2 size={14} className="text-cyan-400" /> Use at least 8 characters</div>
      {error && <p role="alert" className="mt-5 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">{error}</p>}
      <Button disabled={loading} className="mt-7 h-12 w-full gap-2 rounded-xl font-semibold">{loading ? "Creating workspace..." : "Create secure account"}<ArrowRight size={17} /></Button>
      <p className="mt-6 text-center text-sm text-slate-500">Already have an account? <Link className="font-medium text-cyan-300 hover:text-cyan-200" href="/login">Sign in</Link></p>
    </form></section>
  </main>;
}

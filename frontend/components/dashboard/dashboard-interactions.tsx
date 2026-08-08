"use client";

import { ArrowRight, Banknote, Boxes, Database, FileChartColumn, LayoutDashboard, LoaderCircle, Menu, Network, Settings, Share2, ShieldCheck, Sparkles, TrendingUp, Upload, UserRoundSearch, Users, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDashboardState } from "./dashboard-provider";

const navigation = [
  [LayoutDashboard, "Executive Summary", "dashboard-top"], [TrendingUp, "Revenue & Sales", "revenue-overview"], [UserRoundSearch, "Customer Insights", "customer-sentiment"],
  [Network, "Operations", "recommendations"], [Users, "People & HR", "connected-sources"], [Banknote, "Finance", "dashboard-top"], [Boxes, "Inventory & Supply", "alerts-risks"],
  [ShieldCheck, "Risk & Compliance", "alerts-risks"], [Sparkles, "AI Insights", "key-insights"], [FileChartColumn, "Reports", "dashboard-toolbar"], [Database, "Data Sources", "upload"],
] as const;

export function SidebarNavigation({ mobile = false }: { mobile?: boolean }) {
  const { openModal, notify } = useDashboardState();
  function navigate(target: string, label: string) {
    if (target === "upload") { openModal("upload"); return; }
    openModal(null);
    const element = document.getElementById(target) ?? document.getElementById("dashboard-top");
    if (!element) { notify("Section unavailable", `${label} could not be opened.`, "error"); return; }
    if (element.id !== target) notify(label, "This data is summarized in the executive dashboard.", "info");
    element.scrollIntoView({ behavior: "smooth", block: "start" });
    history.replaceState(null, "", `${location.pathname}${location.search}#${target}`);
  }
  return <nav className={mobile ? "space-y-1" : "mt-4 space-y-1"}>{navigation.map(([Icon, label, target], index) => <button type="button" key={label} onClick={() => navigate(target, label)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs transition ${index === 0 ? "border border-violet-400/10 bg-violet-500/10 text-violet-300" : "text-slate-500 hover:bg-slate-800/60 hover:text-slate-200"}`}><Icon size={16} />{label}</button>)}</nav>;
}

export function HeaderActions() {
  const { notify } = useDashboardState();
  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      notify("Report link copied", "The current filters are included in the shared link.", "success");
    } catch { notify("Unable to copy link", "Copy the URL from your browser address bar.", "error"); }
  }
  return <button type="button" onClick={share} className="flex h-10 items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 text-xs text-slate-300"><Share2 size={15} /> Share Report</button>;
}

export function MobileMenuButton() {
  const { openModal } = useDashboardState();
  return <button type="button" onClick={() => openModal("navigation")} aria-label="Open navigation" className="grid h-10 w-10 place-items-center rounded-lg border border-slate-800 xl:hidden"><Menu size={18} /></button>;
}

export function AdvisorActions() {
  const { openModal } = useDashboardState();
  return <><button type="button" onClick={() => openModal("advisor")} className="flex w-full items-center justify-between border-t border-slate-800 pt-3 text-[11px] text-violet-300"><span className="flex items-center gap-2"><Sparkles size={13} /> Ask Sentinel AI</span><span>→</span></button><button type="button" onClick={() => openModal("settings")} className="mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-xs text-slate-500 hover:text-white"><Settings size={16} />Settings</button></>;
}

type Asset = { id: string; kind: string; original_name: string; content_type: string; size_bytes: number; created_at: string };

export function DashboardModals() {
  const router = useRouter();
  const { state, openModal, notify } = useDashboardState();
  const [files, setFiles] = useState<Asset[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [advisorAnswer, setAdvisorAnswer] = useState("");
  const [reducedMotion, setReducedMotion] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);

  const loadFiles = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const response = await fetch("/api/files");
      const result = await response.json() as { items?: Asset[]; detail?: string };
      if (!response.ok) throw new Error(result.detail ?? "Unable to load files");
      setFiles(result.items ?? []);
    } catch (error) { notify("File library unavailable", error instanceof Error ? error.message : "Please retry.", "error"); }
    finally { setLoadingFiles(false); }
  }, [notify]);

  useEffect(() => { if (state.modal === "files") void loadFiles(); }, [state.modal, loadFiles]);
  useEffect(() => { const saved = localStorage.getItem("sentinel-reduced-motion") === "true"; setReducedMotion(saved); document.documentElement.classList.toggle("reduce-motion", saved); }, []);
  useEffect(() => {
    if (!state.modal) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") openModal(null); };
    window.addEventListener("keydown", closeOnEscape);
    return () => { window.removeEventListener("keydown", closeOnEscape); previouslyFocused?.focus(); };
  }, [state.modal, openModal]);

  async function remove(asset: Asset) {
    const response = await fetch(`/api/files/${asset.id}`, { method: "DELETE" });
    if (!response.ok) { notify("Delete failed", `Could not remove ${asset.original_name}.`, "error"); return; }
    setFiles(current => current.filter(item => item.id !== asset.id));
    notify("File removed", `${asset.original_name} was deleted from the server.`, "success");
  }

  function askAdvisor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = String(new FormData(event.currentTarget).get("question") ?? "").trim();
    if (question.length < 3) { notify("Add more detail", "Enter a business question of at least three characters.", "error"); return; }
    setAdvisorAnswer("Review the revenue, risk, and recommendation panels together. Apply a date range, compare regional contribution, and export the filtered report for an auditable decision trail.");
    notify("Insight prepared", "Sentinel analyzed the visible executive context.", "success");
  }

  function saveSettings() {
    localStorage.setItem("sentinel-reduced-motion", String(reducedMotion));
    document.documentElement.classList.toggle("reduce-motion", reducedMotion);
    openModal(null);
    notify("Preferences saved", "Dashboard display preferences were updated on this device.", "success");
  }

  if (!state.modal) return null;
  const title = state.modal === "upload" ? "Upload business data" : state.modal === "files" ? "File library" : state.modal === "advisor" ? "Ask Sentinel AI" : state.modal === "settings" ? "Dashboard settings" : "Navigation";
  return <div className="fixed inset-0 z-40 grid place-items-center bg-black/70 p-3 backdrop-blur-sm print:hidden sm:p-4" role="dialog" aria-modal="true" aria-label={title} onMouseDown={event => { if (event.target === event.currentTarget) openModal(null); }}><section ref={dialogRef} tabIndex={-1} className="max-h-[min(88vh,760px)] w-full max-w-lg overflow-auto rounded-2xl border border-slate-700 bg-[#0d1420] p-4 shadow-2xl outline-none sm:p-5"><header className="mb-4 flex items-center justify-between"><div><h2 className="text-base font-semibold">{title}</h2><p className="mt-1 text-xs text-slate-500">Sentinel AI protected workspace</p></div><button type="button" onClick={() => openModal(null)} aria-label="Close dialog" className="grid h-9 w-9 place-items-center rounded-lg border border-slate-800 text-slate-400 hover:text-white"><X size={16} /></button></header>
    {state.modal === "navigation" && <SidebarNavigation mobile />}
      {state.modal === "upload" && <div><div className="grid min-h-40 place-items-center rounded-xl border border-dashed border-violet-500/40 bg-violet-500/5 p-5 text-center"><span><Upload className="mx-auto text-violet-400" /><span className="mt-3 block text-sm font-medium">Organization dataset onboarding</span><span className="mt-1 block text-xs leading-5 text-slate-500">Preview, validate, append, or replace your tenant-isolated Sales CSV.</span></span></div><div className="mt-4 flex justify-between"><button type="button" onClick={() => openModal("files")} className="text-xs text-violet-300">Open report library</button><button type="button" onClick={() => router.push("/onboarding?manage=1")} className="flex h-10 items-center gap-2 rounded-lg bg-violet-600 px-4 text-xs font-medium">Manage dataset <ArrowRight size={14}/></button></div></div>}
    {state.modal === "files" && <div>{loadingFiles ? <div className="grid h-32 place-items-center"><LoaderCircle className="animate-spin text-violet-400" /></div> : files.length ? <div className="space-y-2">{files.map(asset => <article key={asset.id} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3"><FileChartColumn className="text-violet-400" size={18} /><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{asset.original_name}</p><p className="mt-1 text-[10px] text-slate-600">{asset.kind} | {(asset.size_bytes / 1024).toFixed(1)} KB</p></div><a href={`/api/files/${asset.id}`} target="_blank" rel="noreferrer" className="text-[10px] text-violet-300">View</a><a href={`/api/files/${asset.id}?download=1`} className="text-[10px] text-emerald-300">Download</a><button type="button" onClick={() => void remove(asset)} className="text-[10px] text-rose-400">Delete</button></article>)}</div> : <p className="rounded-xl border border-slate-800 p-6 text-center text-xs text-slate-500">No generated reports or uploaded files yet.</p>}<button type="button" onClick={() => openModal("upload")} className="mt-4 w-full rounded-lg border border-slate-800 py-2.5 text-xs text-violet-300">Upload another file</button></div>}
    {state.modal === "advisor" && <form onSubmit={askAdvisor}><label className="text-xs text-slate-400">Business question<textarea name="question" required minLength={3} maxLength={500} className="mt-2 min-h-28 w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm text-white outline-none focus:border-violet-500" placeholder="Where should the leadership team focus this period?" /></label><button className="mt-3 rounded-lg bg-violet-600 px-4 py-2.5 text-xs font-medium">Generate insight</button>{advisorAnswer && <p className="mt-4 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 text-xs leading-6 text-slate-300">{advisorAnswer}</p>}</form>}
      {state.modal === "settings" && <div><label className="flex items-center justify-between rounded-xl border border-slate-800 p-4"><span><span className="block text-sm">Reduce motion</span><span className="mt-1 block text-xs text-slate-500">Disable smooth scrolling and animated loading effects.</span></span><input type="checkbox" checked={reducedMotion} onChange={event => setReducedMotion(event.target.checked)} className="h-4 w-4 accent-violet-500" /></label><button type="button" onClick={() => router.push("/onboarding?manage=1")} className="mt-3 w-full rounded-lg border border-violet-500/30 py-2.5 text-xs font-medium text-violet-300">Manage organization dataset</button><button type="button" onClick={saveSettings} className="mt-3 w-full rounded-lg bg-violet-600 py-2.5 text-xs font-medium">Save preferences</button></div>}
  </section></div>;
}

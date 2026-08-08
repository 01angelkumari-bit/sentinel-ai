"use client";

import { Download, FileDown, LoaderCircle, Search, SlidersHorizontal, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState, useTransition } from "react";
import { useDashboardState } from "./dashboard-provider";

type Props = { initialStart: string; initialEnd: string; initialQuery: string };

export function DashboardToolbar({ initialStart, initialEnd, initialQuery }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState(initialQuery);
  const [startDate, setStartDate] = useState(initialStart);
  const [endDate, setEndDate] = useState(initialEnd);
  const [lastReport, setLastReport] = useState<{ id: string; original_name: string } | null>(null);
  const { state, setExporting, notify } = useDashboardState();
  const exportController = useRef<AbortController | null>(null);

  useEffect(() => {
    setQuery(initialQuery); setStartDate(initialStart); setEndDate(initialEnd);
  }, [initialQuery, initialStart, initialEnd]);
  useEffect(() => () => exportController.current?.abort(), []);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const start = startDate;
    const end = endDate;
    if (start && end && start > end) {
      notify("Invalid date range", "The start date must be before the end date.", "error");
      return;
    }
    const params = new URLSearchParams();
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    if (query.trim()) params.set("q", query.trim());
    notify("Applying dashboard filters", "Live analytics are being refreshed.", "info");
    startTransition(() => router.push(`/dashboard${params.size ? `?${params}` : ""}`));
  }

  function clearFilters() {
    setQuery("");
    setStartDate("");
    setEndDate("");
    notify("Clearing filters", "Restoring the complete reporting period.", "info");
    startTransition(() => router.push("/dashboard"));
  }

  async function exportCsv() {
    setExporting("csv");
    exportController.current?.abort();
    const controller = new AbortController();
    exportController.current = controller;
    try {
      const params = new URLSearchParams(window.location.search);
      const response = await fetch(`/api/dashboard/export?${params}`, { signal: controller.signal });
      if (!response.ok) { const error = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(error?.detail ?? "Export request failed"); }
      const blob = await response.blob();
      if (!blob.size) throw new Error("The export did not contain any data");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const disposition = response.headers.get("content-disposition") ?? "";
      link.download = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? `sentinel-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      notify("CSV export ready", "Your filtered analytics file was downloaded.", "success");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      notify("CSV export failed", error instanceof Error ? error.message : "Please retry after confirming the API is running.", "error");
    } finally { setExporting(null); }
  }

  async function exportPdf() {
    setExporting("pdf");
    const preview = window.open("about:blank", "_blank");
    try {
      const params = new URLSearchParams(window.location.search);
      const response = await fetch("/api/files/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start_date: params.get("start_date") || null, end_date: params.get("end_date") || null, search: params.get("q") || "" }) });
      const result = await response.json() as { id?: string; original_name?: string; detail?: string };
      if (!response.ok || !result.id || !result.original_name) throw new Error(result.detail ?? "Report generation failed");
      setLastReport({ id: result.id, original_name: result.original_name });
      if (preview) preview.location.href = `/api/files/${result.id}`;
      notify("PDF report generated", "The report was saved securely and opened in a new tab.", "success");
    } catch (error) {
      preview?.close();
      notify("PDF generation failed", error instanceof Error ? error.message : "Please try again.", "error");
    } finally { setExporting(null); }
  }

  return <form onSubmit={applyFilters} className="mb-3 rounded-xl border border-slate-800/90 bg-[#101722] p-3 print:hidden">
    <div className="flex flex-col gap-3 xl:flex-row xl:items-end">
      <label className="min-w-0 flex-1"><span className="mb-1.5 block text-[10px] font-medium uppercase tracking-[.16em] text-slate-500">Search intelligence</span><span className="flex h-10 items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 focus-within:border-violet-500/60"><Search size={15} className="text-slate-500" /><input name="q" value={query} maxLength={100} onChange={event => setQuery(event.target.value)} placeholder="Products, customers or regions" className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-slate-600" /></span></label>
      <div className="grid grid-cols-2 gap-2 sm:flex"><label><span className="mb-1.5 block text-[10px] font-medium uppercase tracking-[.16em] text-slate-500">Start date</span><input name="start_date" type="date" value={startDate} max={endDate || undefined} onChange={event => setStartDate(event.target.value)} className="h-10 w-full rounded-lg border border-slate-800 bg-slate-950/60 px-3 text-xs text-slate-300 outline-none focus:border-violet-500/60" /></label><label><span className="mb-1.5 block text-[10px] font-medium uppercase tracking-[.16em] text-slate-500">End date</span><input name="end_date" type="date" value={endDate} min={startDate || undefined} onChange={event => setEndDate(event.target.value)} className="h-10 w-full rounded-lg border border-slate-800 bg-slate-950/60 px-3 text-xs text-slate-300 outline-none focus:border-violet-500/60" /></label></div>
      <div className="flex flex-wrap gap-2"><button disabled={pending} className="flex h-10 items-center gap-2 rounded-lg bg-violet-600 px-4 text-xs font-medium hover:bg-violet-500 disabled:opacity-60">{pending ? <LoaderCircle size={15} className="animate-spin" /> : <SlidersHorizontal size={15} />} Apply</button><button type="button" onClick={clearFilters} className="grid h-10 w-10 place-items-center rounded-lg border border-slate-800 text-slate-400 hover:text-white" aria-label="Clear filters"><X size={16} /></button><button type="button" onClick={exportCsv} disabled={state.exporting !== null} className="flex h-10 items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 text-xs text-slate-300 disabled:opacity-60">{state.exporting === "csv" ? <LoaderCircle size={15} className="animate-spin" /> : <FileDown size={15} />} CSV</button><button type="button" onClick={exportPdf} disabled={state.exporting !== null} className="flex h-10 items-center gap-2 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 text-xs text-violet-300 disabled:opacity-60">{state.exporting === "pdf" ? <LoaderCircle size={15} className="animate-spin" /> : <Download size={15} />} Generate PDF</button></div>
    </div>
    {lastReport && <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-3"><p className="truncate text-[11px] text-slate-500">Saved report: <span className="text-slate-300">{lastReport.original_name}</span></p><div className="flex gap-2"><a href={`/api/files/${lastReport.id}`} target="_blank" rel="noreferrer" className="rounded-md border border-slate-800 px-2.5 py-1.5 text-[10px] text-violet-300">View PDF</a><a href={`/api/files/${lastReport.id}?download=1`} className="rounded-md bg-violet-600 px-2.5 py-1.5 text-[10px] text-white">Download</a></div></div>}
  </form>;
}

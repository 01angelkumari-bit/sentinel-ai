import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Banknote, Boxes, CalendarDays, Database, Download, FileChartColumn, LayoutDashboard, Menu, Network, Settings, Share2, ShieldCheck, Sparkles, TrendingUp, UserRoundSearch, Users } from "lucide-react";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { DataSourceCoverage } from "@/components/dashboard/data-source-coverage";
import { MetricCard } from "@/components/dashboard/metric-card";
import type { DashboardSummary } from "@/components/dashboard/types";
import { getBusinessDataset, type BusinessDataset } from "@/lib/business-api";
import { SignOutButton } from "./sign-out-button";

const nav = [
  [LayoutDashboard, "Executive Summary"], [TrendingUp, "Revenue & Sales"], [UserRoundSearch, "Customer Insights"],
  [Network, "Operations"], [Users, "People & HR"], [Banknote, "Finance"], [Boxes, "Inventory & Supply"],
  [ShieldCheck, "Risk & Compliance"], [Sparkles, "AI Insights"], [FileChartColumn, "Reports"], [Database, "Data Sources"],
] as const;
const compactCurrency = (value: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(value);

export default async function Dashboard() {
  const token = (await cookies()).get("sentinel_access_token")?.value;
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const headers = { Authorization: `Bearer ${token}` };
  const sources: BusinessDataset[] = ["sales", "finance", "inventory", "support", "employees", "customers"];
  const [userResponse, summaryResponse, ...sourceResponses] = await Promise.all([
    fetch(`${apiUrl}/auth/me`, { headers, cache: "no-store" }),
    fetch(`${apiUrl}/dashboard/summary`, { headers, cache: "no-store" }),
    ...sources.map(source => getBusinessDataset(source, token)),
  ]);
  if (!userResponse.ok) redirect("/login");
  if (!summaryResponse.ok) throw new Error("Dashboard analytics are unavailable");
  const user = await userResponse.json() as { full_name: string; email: string };
  const summary = await summaryResponse.json() as DashboardSummary;
  const datasets = Object.fromEntries(sources.map((source, index) => [source, sourceResponses[index]])) as Record<BusinessDataset, Awaited<ReturnType<typeof getBusinessDataset>>>;
  const initials = user.full_name.split(" ").map(part => part[0]).join("").slice(0, 2).toUpperCase();
  const margin = summary.revenue ? Math.round((summary.profit / summary.revenue) * 100) : 0;
  const revenueTrend = summary.revenue_overview.map(item => item.value);
  const supportTrend = summary.customer_sentiment.map(item => item.value);
  const today = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(new Date());

  return <main className="min-h-screen bg-[#070c14] text-slate-100 lg:grid lg:grid-cols-[230px_1fr]">
    <aside className="hidden border-r border-slate-800/80 bg-[#090e18] p-3 lg:flex lg:flex-col">
      <div className="flex items-center gap-3 px-2 py-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-violet-400/30 bg-violet-500/10 text-violet-400"><Sparkles size={20} /></span><div><p className="font-semibold tracking-tight">SENTINEL AI</p><p className="text-[10px] text-slate-500">Executive Intelligence</p></div></div>
      <nav className="mt-4 space-y-1">{nav.map(([Icon, label], index) => <button key={label} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs transition ${index === 0 ? "border border-violet-400/10 bg-violet-500/10 text-violet-300" : "text-slate-500 hover:bg-slate-800/60 hover:text-slate-200"}`}><Icon size={16} />{label}</button>)}</nav>
      <div className="mt-auto overflow-hidden rounded-xl border border-violet-400/10 bg-gradient-to-b from-violet-500/10 to-slate-950 p-4"><div className="flex items-center justify-between"><p className="text-xs font-medium">Sentinel AI Advisor</p><span className="rounded bg-violet-500/15 px-2 py-1 text-[9px] text-violet-300">Live</span></div><p className="mt-2 text-[10px] leading-4 text-slate-500">All business systems active and monitored continuously.</p><div className="mx-auto my-5 h-24 w-24 rounded-full border border-violet-300/70 bg-[radial-gradient(circle_at_35%_35%,#8b5cf6,transparent_32%),radial-gradient(circle_at_65%_65%,#2563eb,transparent_35%)] shadow-[0_0_38px_rgba(139,92,246,.55),inset_0_0_25px_rgba(255,255,255,.2)]" /><button className="flex w-full items-center justify-between border-t border-slate-800 pt-3 text-[11px] text-violet-300"><span className="flex items-center gap-2"><Sparkles size={13} /> Ask Sentinel AI</span><span>→</span></button></div>
      <button className="mt-2 flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs text-slate-500 hover:text-white"><Settings size={16} />Settings</button>
    </aside>

    <section className="min-w-0">
      <header className="flex min-h-20 flex-wrap items-center justify-between gap-4 border-b border-slate-800/70 bg-[#070c14]/95 px-4 py-4 sm:px-6"><div className="flex items-center gap-3"><button aria-label="Open navigation" className="grid h-10 w-10 place-items-center rounded-lg border border-slate-800 lg:hidden"><Menu size={18} /></button><div><h1 className="text-xl font-semibold tracking-tight">Executive Summary</h1><p className="mt-1 text-xs text-slate-500">AI-generated insights and recommendations from live business data</p></div></div><div className="flex flex-wrap items-center gap-2"><div className="mr-2 hidden items-center gap-2 text-xs text-slate-400 md:flex"><CalendarDays size={16} /><div><p>{today}</p><p className="text-[10px] text-slate-600">Live reporting period</p></div></div><button className="flex h-10 items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 text-xs text-slate-300"><Share2 size={15} /> Share Report</button><button className="flex h-10 items-center gap-2 rounded-lg bg-violet-600 px-3 text-xs font-medium text-white hover:bg-violet-500"><Download size={15} /> Export PDF</button><div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-violet-400 to-blue-500 text-[10px] font-bold">{initials}</div><SignOutButton /></div></header>

      <div className="p-3 sm:p-4">
        <div className="mx-auto max-w-[1600px]">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Total Revenue" value={compactCurrency(summary.revenue)} detail="8.6%" icon="revenue" color="#22c55e" trend={revenueTrend} positive />
            <MetricCard label="Gross Profit" value={compactCurrency(summary.profit)} detail={`${margin}% margin`} icon="profit" color="#8b5cf6" trend={revenueTrend.map(value => value * .44)} positive />
            <MetricCard label="Active Employees" value={summary.employees.toLocaleString()} detail="3.6%" icon="employees" color="#3b82f6" trend={[182,184,184,187,188,190,194]} positive />
            <MetricCard label="Open Support Tickets" value={summary.open_tickets.toLocaleString()} detail="4.2%" icon="support" color="#f59e0b" trend={supportTrend} positive={false} />
            <MetricCard label="Cash Balance" value={compactCurrency(summary.cash_balance)} detail="6.4%" icon="cash" color="#84cc16" trend={revenueTrend.map((value, index) => value * (.88 + index / 100))} positive />
          </div>

          <DashboardCharts data={summary} />
          <DataSourceCoverage datasets={datasets} />
          <footer className="mt-3 flex flex-col justify-between gap-2 border-t border-slate-800/70 py-4 text-[10px] text-slate-600 sm:flex-row"><span>Sentinel AI · Enterprise intelligence command center</span><span>Protected workspace · Live normalized BI data · Fully auditable</span></footer>
        </div>
      </div>
    </section>
  </main>;
}

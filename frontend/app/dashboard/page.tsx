import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Activity, ArrowUpRight, Bell, Bot, ChartNoAxesCombined, CircleGauge, Database, LayoutDashboard, Search, Settings, ShieldCheck, Sparkles, Users } from "lucide-react";
import { SignOutButton } from "./sign-out-button";

const nav = [[LayoutDashboard, "Overview"], [Bot, "AI agents"], [Database, "Data sources"], [ChartNoAxesCombined, "Insights"], [Users, "Team"]] as const;
const metrics = [
  { label: "Active agents", value: "12", change: "+3 this month", icon: Bot, tone: "text-cyan-300 bg-cyan-400/10" },
  { label: "Signals analyzed", value: "48.2K", change: "+18.4%", icon: Activity, tone: "text-violet-300 bg-violet-400/10" },
  { label: "Decisions supported", value: "284", change: "+32 this week", icon: CircleGauge, tone: "text-emerald-300 bg-emerald-400/10" },
  { label: "Data coverage", value: "94%", change: "7 sources live", icon: ShieldCheck, tone: "text-amber-300 bg-amber-400/10" },
] as const;

export default async function Dashboard() {
  const token = (await cookies()).get("sentinel_access_token")?.value;
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const response = await fetch(`${apiUrl}/auth/me`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
  if (!response.ok) redirect("/login");
  const user = await response.json() as { full_name: string; email: string };
  const initials = user.full_name.split(" ").map(part => part[0]).join("").slice(0, 2).toUpperCase();

  return <main className="min-h-screen bg-[#070b14] text-slate-100 lg:grid lg:grid-cols-[252px_1fr]">
    <aside className="hidden border-r border-slate-800/80 bg-[#090e19] p-5 lg:flex lg:flex-col">
      <div className="flex items-center gap-3 px-2 py-3 font-semibold"><span className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-cyan-300"><Sparkles size={19} /></span><span>Sentinel <span className="text-cyan-300">AI</span></span></div>
      <nav className="mt-9 space-y-1">{nav.map(([Icon, label], index) => <button key={label} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${index === 0 ? "border border-cyan-300/10 bg-cyan-400/10 text-cyan-200" : "text-slate-500 hover:bg-slate-800/60 hover:text-slate-200"}`}><Icon size={17} />{label}</button>)}</nav>
      <div className="mt-auto rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="mb-3 flex items-center gap-2 text-xs font-medium text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_12px_#34d399]" /> All systems operational</div><p className="text-xs leading-5 text-slate-500">Agent network secured and processing live signals.</p></div>
      <button className="mt-3 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 hover:text-white"><Settings size={17} /> Settings</button>
    </aside>

    <section className="min-w-0">
      <header className="flex h-20 items-center justify-between border-b border-slate-800/80 px-5 sm:px-8"><div><p className="text-xs text-slate-500">Intelligence workspace</p><h1 className="mt-1 font-semibold">Executive overview</h1></div><div className="flex items-center gap-3"><button aria-label="Search" className="hidden h-10 items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-3 text-sm text-slate-500 sm:flex"><Search size={16} /> Search intelligence <kbd className="ml-5 text-xs">⌘K</kbd></button><button aria-label="Notifications" className="relative grid h-10 w-10 place-items-center rounded-xl border border-slate-800 bg-slate-900/70 text-slate-400"><Bell size={17} /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-cyan-300" /></button><div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-300 to-blue-500 text-xs font-bold text-slate-950">{initials}</div><SignOutButton /></div></header>

      <div className="grid-noise min-h-[calc(100vh-5rem)] p-5 sm:p-8">
        <div className="mx-auto max-w-[1400px]">
          <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end"><div><div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[.2em] text-cyan-300"><span className="h-px w-7 bg-cyan-300" /> Thursday intelligence brief</div><h2 className="text-3xl font-semibold tracking-[-.035em] sm:text-4xl">Good evening, {user.full_name.split(" ")[0]}.</h2><p className="mt-2 text-slate-500">Your agent network identified 7 signals requiring attention.</p></div><button className="flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-400 px-5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"><Sparkles size={16} /> Ask Sentinel</button></div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(({ label, value, change, icon: Icon, tone }) => <article key={label} className="panel-glow rounded-2xl border border-slate-800 bg-slate-900/65 p-5"><div className="flex items-center justify-between"><span className={`grid h-10 w-10 place-items-center rounded-xl ${tone}`}><Icon size={18} /></span><span className="text-xs text-emerald-300">{change}</span></div><p className="mt-6 text-3xl font-semibold tracking-tight">{value}</p><p className="mt-1 text-sm text-slate-500">{label}</p></article>)}</div>

          <div className="mt-4 grid gap-4 xl:grid-cols-[1.45fr_.75fr]">
            <article className="panel-glow overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/65"><div className="flex items-center justify-between border-b border-slate-800 p-5"><div><h3 className="font-semibold">Signal velocity</h3><p className="mt-1 text-xs text-slate-500">Cross-functional activity, last 7 days</p></div><button className="text-xs text-cyan-300">View report</button></div><div className="relative h-72 p-6"><div className="absolute inset-x-6 top-8 flex h-48 flex-col justify-between">{[0,1,2,3].map(line => <div key={line} className="border-t border-dashed border-slate-800" />)}</div><div className="absolute inset-x-8 bottom-12 flex h-44 items-end justify-between gap-3">{[38,52,44,72,59,88,76,92,68,95,84,100].map((height, index) => <div key={index} className="group relative flex-1 rounded-t-sm bg-gradient-to-t from-cyan-500/10 to-cyan-300/80 transition hover:to-cyan-200" style={{height: `${height}%`}}><span className="absolute -top-7 left-1/2 hidden -translate-x-1/2 rounded bg-slate-800 px-2 py-1 text-[10px] group-hover:block">{height * 12}</span></div>)}</div><div className="absolute inset-x-7 bottom-5 flex justify-between text-[10px] uppercase tracking-wider text-slate-600"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div></div></article>
            <article className="panel-glow rounded-2xl border border-slate-800 bg-slate-900/65 p-5"><div className="flex items-center justify-between"><div><h3 className="font-semibold">Priority insights</h3><p className="mt-1 text-xs text-slate-500">Ranked by business impact</p></div><ArrowUpRight size={17} className="text-slate-600" /></div><div className="mt-5 space-y-3">{[["Revenue", "Enterprise expansion signals increased 24% in West region.", "High"], ["Risk", "Supplier latency trend may affect Q4 fulfillment.", "Medium"], ["Growth", "Three accounts show strong cross-sell readiness.", "High"]].map(([type, text, impact], index) => <div key={type} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between"><span className="text-[10px] font-semibold uppercase tracking-widest text-cyan-300">0{index + 1} · {type}</span><span className={`rounded-full px-2 py-1 text-[9px] ${impact === "High" ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-300"}`}>{impact}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{text}</p></div>)}</div></article>
          </div>
        </div>
      </div>
    </section>
  </main>;
}

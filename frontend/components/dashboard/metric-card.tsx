"use client";

import { ArrowDown, ArrowUp, ChartNoAxesCombined, CircleDollarSign, Headphones, Users, WalletCards } from "lucide-react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

type MetricCardProps = { label: string; value: string; detail: string; icon: "revenue" | "profit" | "employees" | "customers" | "support" | "cash"; color: string; trend: number[]; positive?: boolean; comparisonLabel?: string };
const icons = { revenue: CircleDollarSign, profit: ChartNoAxesCombined, employees: Users, customers: Users, support: Headphones, cash: WalletCards };

export function MetricCard({ label, value, detail, icon, color, trend, positive = true, comparisonLabel = "vs prior period" }: MetricCardProps) {
  const Icon = icons[icon]; const TrendIcon = positive ? ArrowUp : ArrowDown; const chartData = trend.map((item, index) => ({ index, value: item }));
  return <article className="panel-glow min-w-0 rounded-xl border border-slate-800/90 bg-[#101722] p-4">
    <div className="flex items-start justify-between"><div><p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</p></div><span className="grid h-10 w-10 place-items-center rounded-full" style={{ backgroundColor: `${color}18`, color }}><Icon size={18} /></span></div>
    <p className={`mt-2 flex items-center gap-1 text-xs ${positive ? "text-emerald-400" : "text-rose-400"}`}><TrendIcon size={12} /> {detail} <span className="text-slate-500">{comparisonLabel}</span></p>
    <div className="mt-2 h-10"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.6} dot={false} /></LineChart></ResponsiveContainer></div>
  </article>;
}

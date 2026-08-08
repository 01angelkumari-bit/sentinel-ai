const labels = {
  sales: "Sales",
  finance: "Finance",
  inventory: "Inventory",
  support: "Support",
  employees: "Employees",
  customers: "Customers",
} as const;

export function DataSourceCoverage({ counts }: { counts: Record<keyof typeof labels, number> }) {
  return <section className="mt-3 rounded-xl border border-slate-800/90 bg-[#101722] p-4">
    <div className="flex items-center justify-between">
      <div><h2 className="text-sm font-semibold text-white">Connected Business APIs</h2><p className="mt-1 text-[11px] text-slate-500">Repository-backed datasets available to executive analytics</p></div>
      <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[10px] font-medium text-emerald-400">6 sources live</span>
    </div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {(Object.keys(labels) as Array<keyof typeof labels>).map(key => <div key={key} className="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2.5"><div className="flex items-center justify-between"><span className="text-[11px] text-slate-400">{labels[key]}</span><span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,.8)]" /></div><p className="mt-1 text-lg font-semibold text-white">{counts[key].toLocaleString()}</p><p className="text-[9px] text-slate-600">records indexed</p></div>)}
    </div>
  </section>;
}

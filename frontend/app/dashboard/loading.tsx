const cards = Array.from({ length: 5 }, (_, index) => index);

export default function DashboardLoading() {
  return <main className="min-h-screen bg-[#070c14] p-2.5 text-slate-100 sm:p-3 xl:p-4 xl:pl-[246px]" aria-label="Loading executive dashboard" aria-busy="true">
    <div className="mx-auto w-full max-w-[3200px] animate-pulse">
      <div className="mb-3 h-16 rounded-xl bg-slate-900" />
      <div className="mb-3 h-20 rounded-xl bg-slate-900" />
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,210px),1fr))] gap-2.5 xl:gap-3">{cards.map(index => <div key={index} className="h-36 rounded-xl bg-slate-900" />)}</div>
      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,.9fr)]"><div className="h-[clamp(280px,28vw,420px)] rounded-xl bg-slate-900" /><div className="h-[clamp(280px,28vw,420px)] rounded-xl bg-slate-900" /></div>
      <span className="sr-only">Loading dashboard analytics</span>
    </div>
  </main>;
}

import type { CustomerLtv, ProductPerformance, RegionPerformance } from "./types";

export function SearchResults({ query, products, customers, regions }: { query: string; products: ProductPerformance[]; customers: CustomerLtv[]; regions: RegionPerformance[] }) {
  if (!query) return null;
  const normalized = query.toLowerCase();
  const matches = [
    ...products.filter(item => `${item.product} ${item.sku}`.toLowerCase().includes(normalized)).map(item => ({ type: "Product", name: item.product, detail: `${item.units_sold.toLocaleString()} units | ${item.revenue.toLocaleString("en-US", { style: "currency", currency: "USD" })}` })),
    ...customers.filter(item => `${item.customer} ${item.region}`.toLowerCase().includes(normalized)).map(item => ({ type: "Customer", name: item.customer, detail: `${item.region} | LTV ${item.lifetime_value.toLocaleString("en-US", { style: "currency", currency: "USD" })}` })),
    ...regions.filter(item => item.region.toLowerCase().includes(normalized)).map(item => ({ type: "Region", name: item.region, detail: `${item.orders.toLocaleString()} orders | ${item.revenue_share_percent}% share` })),
  ].slice(0, 8);
  return <section className="mb-3 rounded-xl border border-violet-500/20 bg-violet-500/[.04] p-4"><div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">Search results for “{query}”</h2><p className="mt-1 text-[11px] text-slate-500">Products, customers and regions from the selected period</p></div><span className="text-xs text-violet-300">{matches.length} matches</span></div>{matches.length ? <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">{matches.map((item, index) => <div key={`${item.type}-${item.name}-${index}`} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span className="text-[9px] uppercase tracking-[.14em] text-violet-400">{item.type}</span><p className="mt-1 truncate text-xs font-medium text-white">{item.name}</p><p className="mt-1 truncate text-[10px] text-slate-500">{item.detail}</p></div>)}</div> : <p className="mt-3 text-xs text-slate-500">No matching business records were found. Try a broader term.</p>}</section>;
}

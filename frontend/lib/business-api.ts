export type ChartPoint = { label: string; value: number };

export type AnalyticsResponse = {
  items: Array<Record<string, unknown>>;
  pagination: { page: number; page_size: number; total: number; pages: number };
  chart_data: ChartPoint[];
};

export type BusinessDataset = "sales" | "finance" | "inventory" | "support" | "employees" | "customers";

export async function getBusinessDataset(
  dataset: BusinessDataset,
  token: string | undefined,
  query = "page=1&page_size=5",
): Promise<AnalyticsResponse> {
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const response = await fetch(`${apiUrl}/${dataset}?${query}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Unable to load ${dataset} data (${response.status})`);
  }
  return response.json() as Promise<AnalyticsResponse>;
}


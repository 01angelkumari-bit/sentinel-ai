import "server-only";
import { cookies } from "next/headers";

export async function authorizedBackendFetch(path: string, init: RequestInit = {}) {
  const token = (await cookies()).get("sentinel_access_token")?.value;
  if (!token) return null;
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ??
    (process.env.NODE_ENV === "production"
      ? "https://sentinel-bi-01angelkumari-api.onrender.com/api/v1"
      : "http://localhost:8000/api/v1");
  return fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}

import "server-only";
import { cookies, headers } from "next/headers";

// Keep this at module scope so Next.js can embed the public build setting in
// the server route bundle as well as in middleware. Vercel does not expose
// build-only NEXT_PUBLIC variables dynamically to a running route handler.
const localUploadMode = process.env.LOCAL_DEMO_MODE === "1" || process.env.NEXT_PUBLIC_LOCAL_DEMO_MODE === "1";

export async function authorizedBackendFetch(path: string, init: RequestInit = {}) {
  const token = (await cookies()).get("sentinel_access_token")?.value;
  const requestIsInUploadMode = (await headers()).get("x-sentinel-local-demo") === "1";
  if (!token && !localUploadMode && !requestIsInUploadMode) return null;
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ??
    (process.env.NODE_ENV === "production"
      ? "https://sentinel-bi-01angelkumari-api.onrender.com/api/v1"
      : "http://localhost:8000/api/v1");
  return fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { ...init.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    cache: "no-store",
  });
}

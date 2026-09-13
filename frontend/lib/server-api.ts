import "server-only";
import { cookies, headers } from "next/headers";

// The hosted Sentinel experience is deliberately upload-first: a visitor
// reaches onboarding immediately and the backend provisions its workspace.
// NODE_ENV is embedded during the Vercel build, unlike build-only public env
// values that are not available dynamically inside route handlers.
const localUploadMode = process.env.NODE_ENV === "production" || process.env.LOCAL_DEMO_MODE === "1" || process.env.NEXT_PUBLIC_LOCAL_DEMO_MODE === "1";

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

import "server-only";
import { cookies, headers } from "next/headers";

// This deployment is deliberately upload-first: a visitor reaches onboarding
// immediately and the backend provisions its shared workspace. Keeping this
// explicit avoids Vercel runtime environment differences re-enabling a login
// requirement inside the server-side API proxy.
const localUploadMode = true;

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

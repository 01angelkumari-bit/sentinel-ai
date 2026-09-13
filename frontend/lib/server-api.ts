import "server-only";
import { cookies } from "next/headers";

const UPLOAD_WORKSPACE_API_URL = "https://sentinel-bi-01angelkumari-api.onrender.com/api/v1";

export async function authorizedBackendFetch(path: string, init: RequestInit = {}) {
  const token = (await cookies()).get("sentinel_access_token")?.value;
  // This hosted upload workspace must not inherit stale project-level Vercel
  // variables left over from the retired login deployment.
  const apiUrl = UPLOAD_WORKSPACE_API_URL;
  return fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { ...init.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    cache: "no-store",
  });
}

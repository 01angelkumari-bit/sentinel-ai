const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export async function apiFetch(path: string, init: RequestInit = {}) { return fetch(`${apiUrl}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init.headers }, cache: "no-store" }); }


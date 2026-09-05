const apiUrl = process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production"
    ? "https://sentinel-bi-01angelkumari-api.onrender.com/api/v1"
    : "http://localhost:8000/api/v1");
const apiOrigin = apiUrl.replace(/\/api\/v1\/?$/, "");

export async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 20_000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The server took too long to respond. Please try again.");
    }
    if (error instanceof TypeError) {
      throw new Error("Unable to connect to the authentication service. Check your connection and try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  return fetchWithTimeout(`${apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
    cache: "no-store",
  });
}

export function authenticationError(status: number, detail?: string) {
  if (detail) return detail;
  const messages: Record<number, string> = {
    400: "Check the information you entered and try again.",
    401: "Invalid email or password.",
    403: "You do not have permission to access this workspace.",
    404: "The authentication service was not found.",
    409: "An account with this email already exists.",
    422: "Some details are invalid. Review the highlighted fields.",
    429: "Too many attempts. Wait a moment before trying again.",
    500: "Authentication failed unexpectedly. Please try again.",
    502: "The authentication service is temporarily unavailable.",
    503: "The authentication service is temporarily unavailable.",
    504: "The authentication service did not respond in time.",
  };
  return messages[status] ?? "Unable to sign in. Please try again.";
}

export function warmAuthenticationApi() {
  if (typeof window === "undefined" || sessionStorage.getItem("sentinel-auth-warmed") === "1") return;
  sessionStorage.setItem("sentinel-auth-warmed", "1");
  void fetchWithTimeout(`${apiOrigin}/health`, { cache: "no-store", mode: "cors" }, 8_000).catch(() => {
    sessionStorage.removeItem("sentinel-auth-warmed");
  });
}

import { NextRequest, NextResponse } from "next/server";

const localUploadMode = process.env.NEXT_PUBLIC_LOCAL_DEMO_MODE === "1";

export function middleware(request: NextRequest) {
  if (localUploadMode) {
    if (request.nextUrl.pathname.startsWith("/login") || request.nextUrl.pathname.startsWith("/register")) {
      return NextResponse.redirect(new URL("/onboarding", request.url));
    }
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-sentinel-local-demo", "1");
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  const token = request.cookies.get("sentinel_access_token")?.value;
  if (!token && (request.nextUrl.pathname.startsWith("/dashboard") || request.nextUrl.pathname.startsWith("/onboarding"))) return NextResponse.redirect(new URL("/login", request.url));
  if (request.nextUrl.pathname === "/login" && request.nextUrl.searchParams.get("expired") === "1") {
    const response = NextResponse.next();
    response.cookies.set("sentinel_access_token", "", { path: "/", maxAge: 0 });
    return response;
  }
  return NextResponse.next();
}
export const config = { matcher: ["/api/:path*", "/dashboard/:path*", "/onboarding/:path*", "/login", "/register"] };

import { NextRequest, NextResponse } from "next/server";
export function middleware(request: NextRequest) { const token = request.cookies.get("sentinel_access_token")?.value; if (!token && request.nextUrl.pathname.startsWith("/dashboard")) return NextResponse.redirect(new URL("/login", request.url)); if (token && ["/login", "/register"].includes(request.nextUrl.pathname)) return NextResponse.redirect(new URL("/dashboard", request.url)); return NextResponse.next(); }
export const config = { matcher: ["/dashboard/:path*", "/login", "/register"] };


import { NextRequest, NextResponse } from "next/server";
export async function POST(request: NextRequest) { const { accessToken } = await request.json() as { accessToken: string }; if (!accessToken) return NextResponse.json({ detail: "Access token is required" }, { status: 400 }); const response = NextResponse.json({ ok: true }); response.cookies.set("sentinel_access_token", accessToken, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 60 * 30 }); return response; }
export async function DELETE() { const response = NextResponse.json({ ok: true }); response.cookies.set("sentinel_access_token", "", { path: "/", maxAge: 0 }); return response; }


import { NextRequest, NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const response = await authorizedBackendFetch("/ai/chat", { method: "POST", body: await request.text(), headers: { "Content-Type": "application/json" } });
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  return new NextResponse(await response.text(), { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "private, no-store" } });
}

import { NextRequest, NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";

async function relay(response: Response | null) {
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const body = await response.text();
  return new NextResponse(body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json", "Cache-Control": "private, no-store" } });
}

export async function GET() { return relay(await authorizedBackendFetch("/datasets/status")); }

export async function POST(request: NextRequest) {
  const filename = request.headers.get("x-filename");
  const mode = request.headers.get("x-import-mode") ?? "initial";
  if (!filename) return NextResponse.json({ detail: "Filename is required" }, { status: 400 });
  return relay(await authorizedBackendFetch("/datasets/imports", { method: "POST", body: await request.arrayBuffer(), headers: { "Content-Type": request.headers.get("content-type") ?? "application/octet-stream", "X-Filename": filename, "X-Import-Mode": mode } }));
}

export async function DELETE() { return relay(await authorizedBackendFetch("/datasets/current", { method: "DELETE" })); }

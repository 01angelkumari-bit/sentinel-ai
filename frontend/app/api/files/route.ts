import { NextRequest, NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";

async function relay(response: Response | null) {
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const body = await response.text();
  return new NextResponse(body, { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" } });
}
export async function GET() {
  return relay(await authorizedBackendFetch("/files"));
}

export async function POST(request: NextRequest) {
  const filename = request.headers.get("x-filename");
  if (!filename) return NextResponse.json({ detail: "Filename is required" }, { status: 400 });
  const body = await request.arrayBuffer();
  const response = await authorizedBackendFetch("/files/uploads", { method: "POST", body, headers: { "Content-Type": request.headers.get("content-type") ?? "application/octet-stream", "X-Filename": filename } });
  return relay(response);
}

import { NextRequest, NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ detail: "Invalid file identifier" }, { status: 400 });
  const disposition = request.nextUrl.searchParams.get("download") === "1" ? "download" : "view";
  const response = await authorizedBackendFetch(`/files/${id}/${disposition}`);
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const headers = new Headers();
  for (const name of ["content-type", "content-disposition", "content-length", "cache-control"]) {
    const value = response.headers.get(name);
    if (value) headers.set(name, value);
  }
  headers.set("Cache-Control", "private, no-store");
  return new NextResponse(response.body, { status: response.status, headers });
}

export async function DELETE(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ detail: "Invalid file identifier" }, { status: 400 });
  const response = await authorizedBackendFetch(`/files/${id}`, { method: "DELETE" });
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  return new NextResponse(null, { status: response.status });
}

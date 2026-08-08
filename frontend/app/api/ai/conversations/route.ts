import { NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";
export async function GET() { const response=await authorizedBackendFetch("/ai/conversations"); if(!response)return NextResponse.json({detail:"Authentication required"},{status:401}); return new NextResponse(await response.text(),{status:response.status,headers:{"Content-Type":"application/json","Cache-Control":"private, no-store"}}); }

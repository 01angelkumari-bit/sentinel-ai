import { NextRequest, NextResponse } from "next/server";
import { authorizedBackendFetch } from "@/lib/server-api";
async function relay(id:string,method:"GET"|"DELETE"){const response=await authorizedBackendFetch(`/ai/conversations/${encodeURIComponent(id)}`,{method});if(!response)return NextResponse.json({detail:"Authentication required"},{status:401});if(response.status===204)return new NextResponse(null,{status:204});return new NextResponse(await response.text(),{status:response.status,headers:{"Content-Type":"application/json","Cache-Control":"private, no-store"}})}
export async function GET(_:NextRequest,{params}:{params:Promise<{id:string}>}){return relay((await params).id,"GET")}
export async function DELETE(_:NextRequest,{params}:{params:Promise<{id:string}>}){return relay((await params).id,"DELETE")}

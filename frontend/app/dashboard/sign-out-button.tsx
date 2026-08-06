"use client";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
export function SignOutButton() { const router = useRouter(); async function signOut() { await fetch("/api/auth/session", { method: "DELETE" }); router.push("/login"); router.refresh(); } return <Button className="hidden h-10 rounded-xl border-slate-800 bg-slate-900/70 text-slate-300 hover:bg-slate-800 sm:inline-flex" variant="outline" onClick={signOut}>Sign out</Button>; }

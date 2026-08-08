"use client";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useState } from "react";
export function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function clearBrowserWorkspace() {
    localStorage.clear();
    sessionStorage.clear();
    if ("caches" in window) {
      const names = await caches.keys();
      await Promise.all(names.map(name => caches.delete(name)));
    }
    if ("databases" in indexedDB) {
      const databases = await indexedDB.databases();
      await Promise.all(databases.flatMap(database => database.name ? [new Promise<void>(resolve => {
        const request = indexedDB.deleteDatabase(database.name!);
        request.onsuccess = request.onerror = request.onblocked = () => resolve();
      })] : []));
    }
  }

  async function signOut() {
    setLoading(true);
    try {
      const response = await fetch("/api/auth/session", { method: "DELETE", cache: "no-store" });
      if (!response.ok) throw new Error("Secure sign out failed");
      await clearBrowserWorkspace();
      router.replace("/login?signedOut=1");
      router.refresh();
    } catch {
      setLoading(false);
    }
  }

  return <Button disabled={loading} className="inline-flex h-10 rounded-xl border-slate-800 bg-slate-900/70 px-3 text-xs text-slate-300 hover:bg-slate-800" variant="outline" onClick={signOut}>{loading ? "Signing out..." : "Sign out"}</Button>;
}

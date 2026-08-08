"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from "react";

type Toast = { id: number; title: string; message?: string; tone: "success" | "error" | "info" };
export type DashboardModal = "upload" | "advisor" | "settings" | "files" | "navigation" | null;
type State = { exporting: "csv" | "pdf" | null; toasts: Toast[]; modal: DashboardModal };
type Action = { type: "export"; value: State["exporting"] } | { type: "toast"; value: Toast } | { type: "dismiss"; id: number } | { type: "modal"; value: DashboardModal };

const DashboardContext = createContext<{ state: State; setExporting: (value: State["exporting"]) => void; notify: (title: string, message?: string, tone?: Toast["tone"]) => void; dismiss: (id: number) => void; openModal: (modal: DashboardModal) => void } | null>(null);

function reducer(state: State, action: Action): State {
  if (action.type === "export") return { ...state, exporting: action.value };
  if (action.type === "toast") return { ...state, toasts: [...state.toasts.slice(-3), action.value] };
  if (action.type === "dismiss") return { ...state, toasts: state.toasts.filter(toast => toast.id !== action.id) };
  return { ...state, modal: action.value };
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { exporting: null, toasts: [], modal: null });
  const timers = useRef(new Map<number, number>());
  const dismiss = useCallback((id: number) => dispatch({ type: "dismiss", id }), []);
  const notify = useCallback((title: string, message?: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    dispatch({ type: "toast", value: { id, title, message, tone } });
    const timer = window.setTimeout(() => { timers.current.delete(id); dispatch({ type: "dismiss", id }); }, 4500);
    timers.current.set(id, timer);
  }, []);
  const setExporting = useCallback((exporting: State["exporting"]) => dispatch({ type: "export", value: exporting }), []);
  const openModal = useCallback((modal: DashboardModal) => dispatch({ type: "modal", value: modal }), []);
  useEffect(() => () => { timers.current.forEach(timer => window.clearTimeout(timer)); timers.current.clear(); }, []);
  const value = useMemo(() => ({ state, setExporting, notify, dismiss, openModal }), [state, setExporting, notify, dismiss, openModal]);
  return <DashboardContext.Provider value={value}>{children}<ToastViewport toasts={state.toasts} dismiss={dismiss} /></DashboardContext.Provider>;
}

export function useDashboardState() {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboardState must be used inside DashboardProvider");
  return context;
}

function ToastViewport({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: number) => void }) {
  return <div aria-live="polite" aria-atomic="true" className="fixed bottom-4 right-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
    {toasts.map(toast => <button key={toast.id} onClick={() => dismiss(toast.id)} className={`rounded-xl border p-4 text-left shadow-2xl backdrop-blur ${toast.tone === "success" ? "border-emerald-500/30 bg-emerald-950/95" : toast.tone === "error" ? "border-rose-500/30 bg-rose-950/95" : "border-violet-500/30 bg-slate-900/95"}`}><p className="text-sm font-medium text-white">{toast.title}</p>{toast.message && <p className="mt-1 text-xs text-slate-300">{toast.message}</p>}</button>)}
  </div>;
}

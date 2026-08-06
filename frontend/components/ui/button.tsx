import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const variants = cva("inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:pointer-events-none disabled:opacity-50", { variants: { variant: { default: "bg-cyan-500 text-slate-950 hover:bg-cyan-400", outline: "border border-slate-600 hover:bg-slate-800" } }, defaultVariants: { variant: "default" } });
export function Button({ className, variant, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants>) { return <button className={cn(variants({ variant }), className)} {...props} />; }


import { redirect } from "next/navigation";
export default function Home() { redirect(process.env.NEXT_PUBLIC_LOCAL_DEMO_MODE === "1" ? "/onboarding" : "/dashboard"); }

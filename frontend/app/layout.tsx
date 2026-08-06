import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Sentinel AI | Business Intelligence Command Center", description: "Governed multi-agent intelligence for decisive business teams." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }

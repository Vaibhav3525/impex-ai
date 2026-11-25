import type { Metadata } from "next";
import "./globals.css";
import AuthGate from "./AuthGate";

export const metadata: Metadata = {
  title: "Global Buyer Acquisition Engine | Indian Exporters",
  description: "AI-Powered International Buyer Discovery, Evidence Verification, and CRM Pipeline Automation",
};

export default function RootLayout({
  children,
}: ReadnextLayoutProps<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full overflow-hidden bg-slate-900 text-slate-100 antialiased">
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}

type ReadnextLayoutProps<T> = T;


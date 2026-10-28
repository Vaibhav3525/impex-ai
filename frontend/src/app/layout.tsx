import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}

type ReadnextLayoutProps<T> = T;


import type { Metadata } from "next";
import { Figtree } from "next/font/google";

import "./globals.css";

// Self-hosted at build time by next/font: no request to Google from the browser.
const figtree = Figtree({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-figtree",
});

export const metadata: Metadata = {
  title: { default: "Leads", template: "%s · Leads" },
  description: "Share your details and resume, and an attorney will reach out.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={figtree.variable}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

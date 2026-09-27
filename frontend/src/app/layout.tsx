import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Leads", template: "%s · Leads" },
  description: "Share your details and resume, and an attorney will reach out.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

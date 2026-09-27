import type { Metadata, Viewport } from "next";

import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Providers } from "@/lib/query";
import { ToastProvider } from "@/components/ui/toast";

export const metadata: Metadata = {
  title: { default: "PayoutFlow", template: "%s · PayoutFlow" },
  description:
    "Creator & Marketplace Payout Engine — earnings, weekly payout batches and simulated processing.",
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#171717",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <Providers>
          <AuthProvider>
            <ToastProvider>{children}</ToastProvider>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}

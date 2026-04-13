import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Catch-up Dashboard",
  description: "Personal priority tracker across Telegram, Notion, GitHub",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0c0f1a] text-[#e2e8f0] min-h-screen`}>
        {children}
      </body>
    </html>
  );
}

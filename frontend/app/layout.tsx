import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import StatusBar from "@/components/StatusBar";

export const metadata: Metadata = {
  title: "F&O Derivatives Analytics Platform",
  description: "Live NSE derivatives analytics, Greeks, vol surface, P&L attribution, and the DOS strategy engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans bg-background text-foreground min-h-screen">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <TopBar />
            <main className="flex-1 p-4 md:p-6 overflow-x-hidden">{children}</main>
            <StatusBar />
          </div>
        </div>
      </body>
    </html>
  );
}

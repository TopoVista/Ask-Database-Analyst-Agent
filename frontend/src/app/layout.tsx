import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import { AppQueryProvider } from "@/components/providers/QueryProvider";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Decision Intelligence Agent",
  description: "AI-powered analytical reasoning for your database",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" className={`${spaceGrotesk.variable} ${jetBrainsMono.variable} dark`}>
        <body className="min-h-screen bg-bg font-sans text-fg antialiased">
          <AppQueryProvider>
            {children}
            <Toaster />
          </AppQueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}


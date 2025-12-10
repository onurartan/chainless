import "@/app/global.css";
import { envx } from "@/lib/envx";
import { RootProvider } from "fumadocs-ui/provider";
import { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Chainless — Build Task-Oriented AI Agents",
  description:
    "Chainless is a lightweight, modular framework to build task-oriented AI agents and orchestrate them in intelligent flows.",
  keywords: [
    "Chainless",
    "chainless ai",
    "pydantic ai",
    "lightweight ai framework",
    "Agent Taskflow",
    "taskflow",
    "agent",
  ],
  metadataBase: new URL(envx.BASE_URL ?? envx.PROD_BASE_URL),

  twitter: {
    card: "summary_large_image",
    title: "Chainless — Build Task-Oriented AI Agents",
    description:
      "Chainless is a lightweight, modular framework to build task-oriented AI agents and orchestrate them in intelligent flows.",
    creator: "@_onuratan",
    images: ["/twitter-image.png"],
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/logo.png",
  },
  alternates: {
    canonical: new URL(envx.BASE_URL ?? envx.PROD_BASE_URL),
  },
};

export default function Layout({ children }: { children: ReactNode }) {
  console.log(envx.DEVELOPER_MESSAGE);
  return (
    <html lang="en" className={inter.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen">
        <RootProvider theme={{ defaultTheme: "dark" }}>{children}</RootProvider>
      </body>
    </html>
  );
}

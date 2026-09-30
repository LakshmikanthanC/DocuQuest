import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeController } from "@/components/theme/ThemeToggle";
import "./globals.css";

const sans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// Editorial serif, used only for display type so the UI keeps a neutral sans.
const display = Instrument_Serif({
  variable: "--font-display-serif",
  subsets: ["latin"],
  weight: "400",
  display: "swap",
});

const SITE_URL = "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "RAG Assistant — Ask your documents, get cited answers",
    template: "%s · RAG Assistant",
  },
  description:
    "Upload PDFs and ask questions in plain language. Answers are generated only from your own documents, with the source page cited for every claim.",
  keywords: [
    "RAG",
    "document assistant",
    "PDF search",
    "semantic search",
    "citations",
    "local LLM",
  ],
  authors: [{ name: "RAG Assistant" }],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "RAG Assistant",
    title: "RAG Assistant — Ask your documents, get cited answers",
    description:
      "Answers generated only from your uploaded PDFs, with the exact page cited for every claim.",
  },
  twitter: {
    card: "summary_large_image",
    title: "RAG Assistant — Ask your documents, get cited answers",
    description:
      "Answers generated only from your uploaded PDFs, with the exact page cited for every claim.",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbfcfd" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0e13" },
  ],
};

// Runs synchronously while the HTML is parsed, so the resolved theme is on
// <html> before the first paint. Without this the page would flash light.
const THEME_SCRIPT = `(function(){try{var p=localStorage.getItem("rag.theme")||"system";var d=p==="dark"||(p==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var e=document.documentElement;e.setAttribute("data-theme",d?"dark":"light");e.setAttribute("data-theme-pref",p)}catch(_){document.documentElement.setAttribute("data-theme","light");document.documentElement.setAttribute("data-theme-pref","system")}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      data-theme-pref="system"
      suppressHydrationWarning
      className={`${sans.variable} ${mono.variable} ${display.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-dvh flex-col">
        <ThemeController />
        {children}
      </body>
    </html>
  );
}

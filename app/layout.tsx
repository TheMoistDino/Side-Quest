import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { Bricolage_Grotesque, Inter } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["600", "800"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Side Quest",
  description: "Pick a vibe, a time window, and a budget. Get a few short adventures nearby.",
};

export const viewport: Viewport = {
  themeColor: "#0e0f11",
};

// Runs before paint so a saved light-mode preference doesn't flash dark first.
const themeScript = `try{var t=localStorage.getItem("sq-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${bricolage.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full font-sans" suppressHydrationWarning>
        <Script id="theme" strategy="beforeInteractive">
          {themeScript}
        </Script>
        {children}
      </body>
    </html>
  );
}

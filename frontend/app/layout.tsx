import type { Metadata } from "next";
import { Inter, Fraunces } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "@/hooks/useTheme";
import { ErrorBoundaryWrapper } from "@/components/ui/ErrorBoundaryWrapper";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

export const metadata: Metadata = {
  title: "NyayaPramaan — Evidence-Verified Legal AI Intelligence",
  description:
    "Next-generation legal AI research platform. Every statutory claim and judgment citation verified by evidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable} dark`} data-theme="dark">
      <body className="antialiased selection:bg-indigo-500/30 selection:text-white min-h-screen">
        <ThemeProvider>
          <AuthProvider>
            <ErrorBoundaryWrapper>
              {children}
            </ErrorBoundaryWrapper>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
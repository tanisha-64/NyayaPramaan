"use client";
import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";

const publicLinks = [
  { href: "/how-it-works", label: "How It Works" },
  { href: "/trust-verification", label: "Trust & Verification" },
  { href: "/game", label: "Legal Rights Game 🎮" },
  { href: "/quiz", label: "Daily Quiz" },
  { href: "/news", label: "Legal News" },
];

const authenticatedLinks = [
  { href: "/public/chat", label: "AI Research" },
  { href: "/app/dashboard", label: "Case Workspace" },
  { href: "/game", label: "Rights Game 🎮" },
  { href: "/quiz", label: "Daily Quiz" },
  { href: "/news", label: "Legal News" },
  { href: "/trust-verification", label: "Trust Engine" },
];

export function TopNav() {
  const [open, setOpen] = useState(false);
  const { user, role, signOut } = useAuth();

  let links = user ? [...authenticatedLinks] : publicLinks;
  if (user && role === "admin") {
    links = [{ href: "/admin", label: "🛡️ Admin Console" }, ...authenticatedLinks];
  }


  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-[#050608]/80 backdrop-blur-2xl">
      <nav className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-3.5">
        <Link href="/" className="flex items-center gap-2.5 no-underline group">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500/20 via-blue-500/20 to-transparent border border-white/15 text-sm shadow-sm group-hover:scale-105 transition-transform">
            ⚖️
          </span>
          <span className="font-[var(--font-serif)] text-lg tracking-wide text-white font-medium">
            NyayaPramaan
          </span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-xs font-medium text-slate-300 hover:text-white transition-colors tracking-wide"
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <>
              <Button href="/public/chat" variant="primary">
                Open Workspace →
              </Button>
              <button
                onClick={() => signOut()}
                className="rounded-xl border border-white/10 px-3.5 py-1.5 text-xs text-slate-400 hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-300 transition-all cursor-pointer"
              >
                Sign Out
              </button>
            </>
          ) : (
            <>
              <Button href="/login" variant="ghost">
                Sign In
              </Button>
              <Button href="/public/chat" variant="primary">
                Launch AI Workspace →
              </Button>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <button
            aria-label="Toggle menu"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-white/80 hover:bg-white/[0.06] cursor-pointer"
            onClick={() => setOpen(!open)}
          >
            {open ? "✕" : "☰"}
          </button>
        </div>
      </nav>

      {open && (
        <div className="flex flex-col gap-3 border-t border-white/10 bg-[#0C0E14] px-6 py-6 md:hidden">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-slate-300 hover:text-white"
              onClick={() => setOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          <div className="mt-2 flex flex-col gap-2 pt-2 border-t border-white/[0.08]">
            {user ? (
              <>
                <Button href="/public/chat" variant="primary">
                  Open Workspace
                </Button>
                <button
                  onClick={() => {
                    setOpen(false);
                    signOut();
                  }}
                  className="rounded-xl border border-red-500/20 bg-red-500/10 py-2.5 text-center text-xs text-red-300 hover:bg-red-500/20"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Button href="/login" variant="secondary">
                  Sign In
                </Button>
                <Button href="/public/chat" variant="primary">
                  Launch AI Workspace
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
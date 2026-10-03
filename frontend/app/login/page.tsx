"use client";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { supabase } from "@/lib/supabaseClient";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUnconfirmed, setIsUnconfirmed] = useState(false);
  const [resendSent, setResendSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setIsUnconfirmed(false);

    try {
      const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });

      if (signInError) {
        if (signInError.message.toLowerCase().includes("email not confirmed")) {
          setIsUnconfirmed(true);
          setError("Your email address is not confirmed yet. Please check your inbox or click below to resend the verification link.");
        } else {
          setError(signInError.message);
        }
        setLoading(false);
        return;
      }

      if (data?.session) {
        const userEmail = (data.user?.email || "").toLowerCase().trim();
        const adminEmail = (process.env.NEXT_PUBLIC_ADMIN_EMAIL || "mitanisha74@gmail.com").toLowerCase().trim();
        const isAdminUser = userEmail === adminEmail || userEmail === "mitanisha74@gmail.com";

        let defaultTarget = "/";
        if (isAdminUser) {
          defaultTarget = "/";
        } else {
          const role = data.user?.user_metadata?.role ?? "public";
          defaultTarget = role === "professional" ? "/app/dashboard" : "/public/chat";
        }

        const targetUrl = redirectParam || defaultTarget;
        
        // Immediate redirect
        if (typeof window !== "undefined") {
          window.location.href = targetUrl;
        } else {
          router.push(targetUrl);
        }
        return;
      }
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred. Please try again.");
    }

    setLoading(false);
  }

  async function handleResend() {
    try {
      await supabase.auth.resend({ type: "signup", email });
      setResendSent(true);
    } catch {
      // ignore
    }
  }


  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to your evidence-backed legal intelligence workspace."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300 [data-theme=light]:text-slate-700">
            Email Address
          </label>
          <Input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="advocate@court.in"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300 [data-theme=light]:text-slate-700">
            Password
          </label>
          <Input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
          />
        </div>

        {error && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-300">
            <div className="flex items-start gap-2">
              <span className="text-base">⚠️</span>
              <div className="flex-1">
                <p className="leading-relaxed">{error}</p>
                {isUnconfirmed && (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendSent}
                    className="mt-2 inline-block font-semibold text-blue-400 hover:text-blue-300 underline cursor-pointer"
                  >
                    {resendSent ? "✓ Verification link resent to your email!" : "Click here to resend verification link →"}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}


        <div className="pt-2">
          <Button
            type="submit"
            disabled={loading}
            variant="primary"
            className="w-full justify-center py-3 text-sm font-semibold shadow-lg hover:shadow-indigo-500/20"
          >
            {loading ? "Authenticating..." : "Sign In to Workspace →"}
          </Button>
        </div>

        <div className="flex items-center justify-between pt-3 text-xs text-white/50 [data-theme=light]:text-slate-500">
          <Link
            href="/forgot-password"
            className="hover:text-amber-400 transition-colors no-underline"
          >
            Forgot password?
          </Link>
          <Link
            href="/register"
            className="text-blue-400 hover:text-blue-300 font-medium transition-colors no-underline"
          >
            Create an account →
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#050608]" />}>
      <LoginForm />
    </Suspense>
  );
}
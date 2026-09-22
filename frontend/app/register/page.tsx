"use client";
import { useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { supabase } from "@/lib/supabaseClient";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"public" | "professional">("public");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [resendSent, setResendSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const redirectUrl = typeof window !== "undefined" ? `${window.location.origin}/login` : "http://localhost:3000/login";

    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { role },
        emailRedirectTo: redirectUrl,
      },
    });

    if (signUpError) {
      setError(signUpError.message);
      setLoading(false);
      return;
    }

    if (data.user && data.user.identities && data.user.identities.length === 0) {
      setError("An account with this email already exists. Please sign in instead.");
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  }

  async function handleResendEmail() {
    try {
      await supabase.auth.resend({ type: "signup", email });
      setResendSent(true);
    } catch {
      // ignore
    }
  }

  if (success) {
    return (
      <AuthLayout
        title="Check Your Inbox"
        subtitle="We've sent an official verification link to activate your research account."
      >
        <div className="text-center py-4">
          <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20 text-3xl text-emerald-400 border border-emerald-500/30 shadow-lg animate-pulse">
            ✉️
          </div>
          <p className="text-sm font-semibold text-white mb-2">
            Verification email sent to {email}
          </p>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed">
            Please check your inbox (or spam folder) and click the verification link to confirm your account. Once verified, sign in below.
          </p>
          <div className="space-y-3">
            <Button href="/login" variant="primary" className="w-full justify-center py-3">
              Proceed to Sign In →
            </Button>
            <button
              type="button"
              onClick={handleResendEmail}
              disabled={resendSent}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors cursor-pointer block mx-auto pt-2"
            >
              {resendSent ? "✓ Verification link resent!" : "Didn't receive email? Resend verification link"}
            </button>
          </div>
        </div>
      </AuthLayout>
    );
  }


  return (
    <AuthLayout
      title="Create Account"
      subtitle="Join NyayaPramaan for citation-grounded legal AI research."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300 [data-theme=light]:text-slate-700">
            Account Type
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setRole("public")}
              className={`flex items-center justify-center gap-1.5 rounded-xl border p-2.5 text-xs font-medium transition-all cursor-pointer ${
                role === "public"
                  ? "border-blue-500 bg-blue-600/20 text-blue-300 shadow-sm [data-theme=light]:border-blue-600 [data-theme=light]:bg-blue-50 [data-theme=light]:text-blue-700"
                  : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 [data-theme=light]:border-black/10 [data-theme=light]:bg-black/[0.02]"
              }`}
            >
              <span>👤</span>
              <span>Citizen / Student</span>
            </button>
            <button
              type="button"
              onClick={() => setRole("professional")}
              className={`flex items-center justify-center gap-1.5 rounded-xl border p-2.5 text-xs font-medium transition-all cursor-pointer ${
                role === "professional"
                  ? "border-amber-500 bg-amber-600/20 text-amber-300 shadow-sm [data-theme=light]:border-amber-600 [data-theme=light]:bg-amber-50 [data-theme=light]:text-amber-700"
                  : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 [data-theme=light]:border-black/10 [data-theme=light]:bg-black/[0.02]"
              }`}
            >
              <span>⚖️</span>
              <span>Legal Professional</span>
            </button>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300 [data-theme=light]:text-slate-700">
            Email Address
          </label>
          <Input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="advocate@example.com"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300 [data-theme=light]:text-slate-700">
            Password (Min. 6 Characters)
          </label>
          <Input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 [data-theme=light]:text-amber-800">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div className="pt-2">
          <Button
            type="submit"
            disabled={loading}
            variant="primary"
            className="w-full justify-center py-3 text-sm font-semibold shadow-lg hover:shadow-indigo-500/20"
          >
            {loading ? "Creating Account..." : "Create Free Account →"}
          </Button>
        </div>

        <p className="pt-3 text-center text-xs text-white/50 [data-theme=light]:text-slate-500">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-blue-400 hover:text-blue-300 font-medium transition-colors no-underline"
          >
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { supabase } from "@/lib/supabaseClient";
import type { User } from "@supabase/supabase-js";

type Role = "public" | "professional" | "admin";

type AuthContextValue = {
  user: User | null;
  role: Role;
  isAdmin: boolean;
  loading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const SUPER_ADMIN_EMAILS = [
  (process.env.NEXT_PUBLIC_ADMIN_EMAIL || "mitanisha74@gmail.com").toLowerCase().trim(),
];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession()
      .then(({ data, error }) => {
        if (error) console.error("[useAuth] getSession error:", error);
        setUser(data.session?.user ?? null);
      })
      .catch((e) => {
        console.error("[useAuth] getSession threw:", e);
        setUser(null);
      })
      .finally(() => setLoading(false));

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  const userEmail = (user?.email || "").toLowerCase().trim();
  const isAdmin = !!userEmail && SUPER_ADMIN_EMAILS.includes(userEmail);

  let role: Role = "public";
  if (isAdmin) {
    role = "admin";
  } else {
    const rawRole = (user?.user_metadata?.role as Role) ?? "public";
    role = rawRole === "admin" ? "public" : (rawRole === "professional" ? "professional" : "public");
  }

  async function signOut() {
    await supabase.auth.signOut();
    setUser(null);
    window.location.href = "/login";
  }

  return (
    <AuthContext.Provider value={{ user, role, isAdmin, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
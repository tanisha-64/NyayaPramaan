"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { supabase } from "@/lib/supabaseClient";
import type { User } from "@supabase/supabase-js";

export type Role = "public" | "professional" | "admin";

export type AuthContextValue = {
  user: User | null;
  role: Role;
  isAdmin: boolean;
  activePersona: Role;
  setActivePersona: (p: Role) => void;
  loading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Recognized super-admin emails:
const DEFAULT_SUPER_ADMIN_EMAILS = [
  "mitanisha74@gmail.com",
];

function getSuperAdminEmails(): string[] {
  const envEmail = process.env.NEXT_PUBLIC_ADMIN_EMAIL;
  const list = [...DEFAULT_SUPER_ADMIN_EMAILS];
  if (envEmail) {
    envEmail.split(",").forEach((e) => {
      const trimmed = e.trim().toLowerCase();
      if (trimmed && !list.includes(trimmed)) {
        list.push(trimmed);
      }
    });
  }
  return list;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [activePersona, setActivePersona] = useState<Role>("admin");

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
  const superAdmins = getSuperAdminEmails();
  const isAdmin = Boolean(userEmail && superAdmins.includes(userEmail));

  // Determine actual base role:
  let role: Role = "public";
  if (isAdmin) {
    role = "admin";
  } else {
    // Normal users can ONLY ever be 'public' or 'professional' (never admin)
    const rawRole = (user?.user_metadata?.role as Role) ?? "public";
    role = rawRole === "professional" ? "professional" : "public";
  }

  async function signOut() {
    await supabase.auth.signOut();
    setUser(null);
    window.location.href = "/login";
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAdmin,
        activePersona,
        setActivePersona,
        loading,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

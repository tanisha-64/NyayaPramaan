
"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

import { supabase } from "@/lib/supabaseClient";

import type { User } from "@supabase/supabase-js";



type Role = "public" | "professional" | "admin";

type AuthContextValue = { user: User | null; role: Role; loading: boolean; signOut: () => Promise<void> };

const AuthContext = createContext<AuthContextValue | undefined>(undefined);



export function AuthProvider({ children }: { children: ReactNode }) {

  const [user, setUser] = useState<User | null>(null);

  const [loading, setLoading] = useState(true);



  useEffect(() => {

    supabase.auth.getSession()

      .then(({ data }) => setUser(data.session?.user ?? null))

      .catch(() => setUser(null))

      .finally(() => setLoading(false));



    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {

      setUser(session?.user ?? null);

    });

    return () => listener.subscription.unsubscribe();

  }, []);



  const role = (user?.user_metadata?.role as Role) ?? "public";



  async function signOut() {

    await supabase.auth.signOut();

    setUser(null);

    window.location.href = "/login";

  }



  return <AuthContext.Provider value={{ user, role, loading, signOut }}>{children}</AuthContext.Provider>;

}



export function useAuth() {

  const ctx = useContext(AuthContext);

  if (!ctx) throw new Error("useAuth must be used within AuthProvider");

  return ctx;

}


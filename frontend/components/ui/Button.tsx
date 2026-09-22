import Link from "next/link";
import { ReactNode } from "react";

type ButtonProps = {
  children: ReactNode;
  href?: string;
  variant?: "primary" | "secondary" | "ghost" | "gold";
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
};

const variants = {
  primary:
    "bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] text-slate-950 font-semibold shadow-md hover:brightness-110 border border-amber-300/30",
  secondary:
    "border border-white/15 bg-white/[0.04] text-slate-300 hover:border-blue-500/40 hover:bg-white/[0.08] hover:text-white shadow-xs",
  ghost:
    "text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] border border-transparent",
  gold:
    "bg-[#B8925A] text-slate-950 font-semibold hover:brightness-110",
};

export function Button({
  children,
  href,
  variant = "primary",
  onClick,
  type = "button",
  disabled,
  className = "",
}: ButtonProps) {
  const baseClasses = `inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-xs font-medium tracking-wide transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer ${variants[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={baseClasses}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={baseClasses}>
      {children}
    </button>
  );
}
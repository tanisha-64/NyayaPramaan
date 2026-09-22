import { InputHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input(props, ref) {
    return (
      <input
        ref={ref}
        {...props}
        className={`w-full rounded-lg border border-white/[0.12] bg-white/[0.03] px-3.5 py-2.5 text-xs text-slate-100 placeholder:text-white/30 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all ${props.className ?? ""}`}
      />
    );
  }
);
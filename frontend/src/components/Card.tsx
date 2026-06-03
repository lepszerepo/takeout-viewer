import { PropsWithChildren } from "react";

export function Card({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return (
    <div className={`bg-white border border-slate-200 rounded-lg shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ children }: PropsWithChildren) {
  return <div className="px-4 py-3 border-b border-slate-200 font-medium text-slate-800">{children}</div>;
}

export function CardBody({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return <div className={`p-4 ${className}`}>{children}</div>;
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-2xl font-semibold text-slate-900 mt-1">{value}</div>
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}

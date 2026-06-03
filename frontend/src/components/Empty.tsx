interface Props {
  title: string;
  hint?: string;
  children?: React.ReactNode;
}

export default function Empty({ title, hint, children }: Props) {
  return (
    <div className="border border-dashed border-slate-300 rounded-lg p-8 text-center bg-white">
      <div className="text-slate-700 font-medium">{title}</div>
      {hint && <div className="text-sm text-slate-500 mt-2 whitespace-pre-line">{hint}</div>}
      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}

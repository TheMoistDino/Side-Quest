type Props = {
  step: number;
  children: React.ReactNode;
  htmlFor?: string;
  value?: string;
};

export function FieldLabel({ step, children, htmlFor, value }: Props) {
  return (
    <div className="flex items-baseline justify-between">
      <label htmlFor={htmlFor} className="text-xs font-bold uppercase tracking-caps">
        {step} · {children}
      </label>
      {value && <span className="font-display text-2xl font-extrabold">{value}</span>}
    </div>
  );
}

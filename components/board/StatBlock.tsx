type Props = {
  value: string;
  label: string;
  labelClass?: string;
};

export function StatBlock({ value, label, labelClass = "text-muted" }: Props) {
  return (
    <div className="flex flex-col whitespace-nowrap">
      <span className="font-display text-lg leading-6 font-extrabold">{value}</span>
      <span className={`text-xs ${labelClass}`}>{label}</span>
    </div>
  );
}

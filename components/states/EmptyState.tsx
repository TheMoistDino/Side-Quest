type Props = { onEdit: () => void };

export function EmptyState({ onEdit }: Props) {
  return (
    <div className="flex flex-col items-start gap-5 rounded-2xl border border-line p-8">
      <div className="flex flex-col gap-2">
        <h2 className="font-display text-[28px] leading-8 font-extrabold tracking-tight">No quests in range</h2>
        <p className="max-w-md text-[15px] text-muted">
          Nothing fit those answers. Try a bigger budget, a longer window, or a wider radius.
        </p>
      </div>
      <button type="button" onClick={onEdit} className="rounded-full bg-sign px-[22px] py-3 text-[15px] font-semibold text-on-sign transition hover:brightness-105">
        Adjust answers
      </button>
    </div>
  );
}

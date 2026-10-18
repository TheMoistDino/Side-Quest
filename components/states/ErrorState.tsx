type Props = {
  message: string;
  onRetry: () => void;
  onEdit: () => void;
};

export function ErrorState({ message, onRetry, onEdit }: Props) {
  return (
    <div role="alert" className="flex flex-1 animate-rise flex-col justify-center gap-6 py-10">
      <div className="flex flex-col gap-2.5">
        <span className="text-[13px] font-semibold text-danger">Quest failed</span>
        <h1 className="font-display text-[40px] leading-[42px] font-extrabold tracking-tight">{message}</h1>
        <p className="text-[15px] text-muted">Your answers are saved.</p>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full bg-sign px-[22px] py-3.5 text-[15px] font-semibold text-on-sign transition hover:brightness-105"
        >
          Try again
        </button>
        <button type="button" onClick={onEdit} className="rounded-full px-4 py-3.5 text-[15px] font-medium text-muted transition hover:text-text">
          Edit answers
        </button>
      </div>
    </div>
  );
}

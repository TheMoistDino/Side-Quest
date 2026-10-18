"use client";

import { useState } from "react";

type Props = {
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  /** How the value reads when not editing, e.g. "$40", "Free", "10 mi". */
  format: (value: number) => string;
  /** Shown beside the input while typing, e.g. "$" or "mi". */
  prefix?: string;
  suffix?: string;
  label: string;
  className?: string;
  /** Called when a typed value had to be clamped down to `max`. */
  onOverflow?: () => void;
};

/** A big display number that turns into a text field when tapped. Enter or blur commits; Escape cancels. */
export function EditableNumber({ value, min, max, onChange, format, prefix, suffix, label, className = "", onOverflow }: Props) {
  const [draft, setDraft] = useState<string | null>(null);

  function commit() {
    if (draft === null) return;
    const n = Math.round(Number(draft));
    if (draft.trim() !== "" && Number.isFinite(n)) {
      if (n > max) onOverflow?.();
      onChange(Math.min(max, Math.max(min, n)));
    }
    setDraft(null);
  }

  if (draft === null) {
    return (
      <button
        type="button"
        onClick={() => setDraft(String(value))}
        aria-label={`${label}: ${format(value)}. Tap to type a number.`}
        className={`cursor-text underline decoration-line decoration-dashed decoration-2 underline-offset-[10px] transition hover:decoration-muted ${className}`}
      >
        {format(value)}
      </button>
    );
  }

  return (
    <span className={`inline-flex items-baseline ${className}`}>
      {prefix && <span aria-hidden>{prefix}</span>}
      <input
        autoFocus
        aria-label={label}
        inputMode="numeric"
        enterKeyHint="done"
        value={draft}
        onChange={(e) => setDraft(e.target.value.replace(/[^\d]/g, "").slice(0, String(max).length + 1))}
        onFocus={(e) => e.target.select()}
        onBlur={commit}
        onKeyDown={(e) => {
          // Enter commits without submitting the step's form.
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          } else if (e.key === "Escape") {
            setDraft(null);
          }
        }}
        style={{ width: `${Math.max(draft.length, 1) + 0.15}ch` }}
        className="min-w-0 border-b-2 border-sign bg-transparent p-0 outline-none [font:inherit] [letter-spacing:inherit]"
      />
      {suffix && <span aria-hidden>{suffix}</span>}
    </span>
  );
}

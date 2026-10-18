import type { Answers } from "@/components/wizard/answers";
import { categoryLabel } from "@/components/wizard/VibeOptions";
import { formatBudget, formatTime } from "@/lib/format";

type Props = {
  answers: Answers;
  onEdit: (step: number) => void;
};

export function AnswerSummary({ answers, onEdit }: Props) {
  // Same order as the wizard steps, so index === step.
  const items = [
    categoryLabel(answers.category),
    answers.start && answers.end ? `${formatTime(answers.start)} – ${formatTime(answers.end)}` : "Any time",
    `${formatBudget(answers.budget)} pp`,
    answers.location.label || "Near you",
    `${answers.distance} mi`,
    `${answers.groupSize} ${answers.groupSize === 1 ? "person" : "people"}`,
  ];
  return (
    <ul aria-label="Your answers. Tap one to change it." className="flex flex-wrap gap-1.5">
      {items.map((label, step) => (
        <li key={step}>
          <button
            type="button"
            onClick={() => onEdit(step)}
            className="rounded-full border border-line px-3 py-1.5 text-[13px] font-medium text-muted transition hover:border-muted hover:text-text"
          >
            {label}
          </button>
        </li>
      ))}
    </ul>
  );
}

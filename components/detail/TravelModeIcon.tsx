import type { Stop } from "@/types/quest";

type Props = { mode: Stop["travelMode"] };

export function TravelModeIcon({ mode }: Props) {
  const common = {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (mode === "walking") {
    return (
      <svg {...common}>
        <circle cx="13" cy="4" r="2" />
        <path d="M10 21l2-6 3 3v3M8 12l2-4 4 1 2 3 3 1M12 15l-1-4" />
      </svg>
    );
  }
  if (mode === "transit") {
    return (
      <svg {...common}>
        <rect x="5" y="3" width="14" height="14" rx="3" />
        <path d="M5 11h14M9 21l-2-4M15 21l2-4" />
        <circle cx="9" cy="14" r=".5" />
        <circle cx="15" cy="14" r=".5" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M5 17h14M6 17l1.5-6h9L18 17M8 17v2M16 17v2" />
      <circle cx="8.5" cy="14" r=".5" />
      <circle cx="15.5" cy="14" r=".5" />
    </svg>
  );
}

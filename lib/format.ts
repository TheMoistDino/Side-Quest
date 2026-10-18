export const BUDGET_MAX = 100;

export function formatMoney(amount: number, opts: { estimate?: boolean } = {}): string {
  const value = amount === 0 ? "Free" : `$${Number.isInteger(amount) ? amount : amount.toFixed(2)}`;
  return opts.estimate && amount !== 0 ? `~${value}` : value;
}

export function formatBudget(amount: number): string {
  if (amount === 0) return "Free";
  return amount >= BUDGET_MAX ? `$${BUDGET_MAX}+` : `$${amount}`;
}

export function formatMiles(miles: number): string {
  if (miles < 0.1) return "< 0.1 mi";
  return `${miles < 10 ? miles.toFixed(1).replace(/\.0$/, "") : Math.round(miles)} mi`;
}

export function formatDuration(minutes: number): string {
  const m = Math.round(minutes);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest === 0 ? `${h} hr` : `${h} hr ${rest} min`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Value for <input type="datetime-local"> in the user's local time zone. */
export function toDateTimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMoney(value: string | number | null | undefined, opts?: { sign?: boolean }): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(n)) return "—";
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(Math.abs(n));
  if (n < 0) return `−${formatted}`;
  if (opts?.sign && n > 0) return `+${formatted}`;
  return formatted;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "—";
  const seconds = Math.floor((Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [
    [60, "minute"], [24, "hour"], [7, "day"], [4.35, "week"], [12, "month"],
  ];
  let amount = seconds / 60;
  for (let i = 0; i < units.length; i++) {
    const [div, name] = units[i];
    if (amount < div || i === units.length - 1) {
      const rounded = Math.floor(amount);
      return `${rounded} ${name}${rounded === 1 ? "" : "s"} ago`;
    }
    amount = amount / div;
  }
  return "—";
}

export function periodLabel(start: string, end: string): string {
  const s = new Date(`${start}T00:00:00`);
  const e = new Date(`${end}T00:00:00`);
  const sopts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const sameYear = s.getFullYear() === e.getFullYear();
  const eopts: Intl.DateTimeFormatOptions = sameYear
    ? { month: "short", day: "numeric", year: "numeric" }
    : { month: "short", day: "numeric", year: "numeric" };
  return `${s.toLocaleDateString("en-US", sopts)} – ${e.toLocaleDateString("en-US", eopts)}`;
}

export function weekStartLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
    month: "short", day: "numeric",
  });
}

export function monthLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
    month: "short", year: "numeric",
  });
}

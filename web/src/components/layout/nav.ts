import {
  BadgeDollarSign, Banknote, CalendarClock, Coins, FileClock,
  LayoutDashboard, ScrollText, Settings2, UserRound, Users, Wallet, Briefcase,
} from "lucide-react";

import type { Role } from "@/lib/types";

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Role[];
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard",      label: "Dashboard",    icon: LayoutDashboard, roles: ["ADMIN", "CREATOR"] },
  { href: "/creators",       label: "Creators",     icon: Users,           roles: ["ADMIN"] },
  { href: "/jobs",           label: "Jobs",         icon: Briefcase,       roles: ["ADMIN", "CREATOR"] },
  { href: "/earnings",       label: "Earnings",     icon: Coins,           roles: ["ADMIN", "CREATOR"] },
  { href: "/payout-rules",   label: "Payout Rules", icon: Settings2,       roles: ["ADMIN"] },
  { href: "/payout-batches", label: "Payout Batches", icon: CalendarClock, roles: ["ADMIN"] },
  { href: "/payouts",        label: "Payouts",      icon: Wallet,          roles: ["ADMIN", "CREATOR"] },
  { href: "/audit-logs",     label: "Audit Logs",   icon: ScrollText,      roles: ["ADMIN"] },
  { href: "/profile",        label: "Profile",      icon: UserRound,       roles: ["ADMIN", "CREATOR"] },
];

export function navForRole(role: Role): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

export { BadgeDollarSign, Banknote, FileClock };

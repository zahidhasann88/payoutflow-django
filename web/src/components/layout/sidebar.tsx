"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BadgeDollarSign } from "lucide-react";

import { navForRole } from "@/components/layout/nav";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const items = navForRole(user?.role ?? "CREATOR");

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <BadgeDollarSign className="h-4.5 w-4.5" />
        </span>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-white">PayoutFlow</div>
          <div className="text-[10px] uppercase tracking-widest text-white/40">Payout Engine</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Main navigation">
        {items.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 p-4 text-[11px] leading-relaxed text-white/40">
        Weekly payouts · Simulated processing
        <br />
        Portfolio project — no real money moves.
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 lg:block">
      <SidebarContent />
    </aside>
  );
}

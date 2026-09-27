"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight, Banknote, CalendarClock, CircleDollarSign, Coins,
  Landmark, Percent, Users, Wallet,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { BarChart } from "@/components/shared/bar-chart";
import { ErrorState, CardsSkeleton, EmptyState, TableSkeleton } from "@/components/shared/states";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AdminDashboard, ApiEnvelope, CreatorDashboard } from "@/lib/types";
import { formatDateTime, formatMoney, monthLabel, periodLabel, timeAgo, weekStartLabel } from "@/lib/utils";

export default function DashboardPage() {
  const { user, isAdmin } = useAuth();
  return isAdmin ? <AdminDashboardView name={user?.name ?? ""} /> : <CreatorDashboardView name={user?.name ?? ""} />;
}

function AdminDashboardView({ name }: { name: string }) {
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } =
    useQuery({
      queryKey: ["dashboard", "admin"],
      queryFn: () => api.get<ApiEnvelope<AdminDashboard>>("/dashboard/admin/"),
    });

  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const d = data?.data;
  const cards = d?.cards;

  return (
    <div>
      <PageHeader title={`Welcome back, ${name.split(" ")[0]}`}
                  description="Platform overview — earnings, fees and weekly payout operations." />

      {isLoading || !cards ? (
        <CardsSkeleton count={5} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Total Creators" value={cards.total_creators} icon={Users} />
          <StatCard label="This Month's Gross" value={formatMoney(cards.month_gross)} icon={Coins} />
          <StatCard label="Platform Fees" value={formatMoney(cards.month_platform_fees)}
                    hint="Collected this month" icon={Percent} />
          <StatCard label="Total Paid" value={formatMoney(cards.total_paid)} accent="success"
                    hint={`${cards.total_paid_count} payouts`} icon={Landmark} />
          <StatCard label="Pending Payouts" value={formatMoney(cards.pending_payout_amount)} accent="warning"
                    hint={`${cards.pending_payout_count} in open batches · ${formatMoney(cards.pending_earnings_amount)} unbatched`}
                    icon={Wallet} />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-semibold">Earnings overview</CardTitle>
            <Tabs defaultValue="weekly" className="w-auto">
              <TabsList className="h-8">
                <TabsTrigger value="weekly" className="text-xs">Weekly</TabsTrigger>
                <TabsTrigger value="monthly" className="text-xs">Monthly</TabsTrigger>
              </TabsList>
              <TabsContent value="weekly" className="mt-4">
                <BarChart loading={isLoading}
                  data={(d?.chart.weekly ?? []).map((r) => ({
                    label: weekStartLabel(r.period),
                    gross: parseFloat(r.gross), fees: parseFloat(r.fees), net: parseFloat(r.net),
                  }))} />
              </TabsContent>
              <TabsContent value="monthly" className="mt-4">
                <BarChart loading={isLoading}
                  data={(d?.chart.monthly ?? []).map((r) => ({
                    label: monthLabel(r.period),
                    gross: parseFloat(r.gross), fees: parseFloat(r.fees), net: parseFloat(r.net),
                  }))} />
              </TabsContent>
            </Tabs>
          </CardHeader>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
              </div>
            ) : (d?.recent_activity.length ?? 0) === 0 ? (
              <EmptyState title="No activity yet" />
            ) : (
              <ul className="space-y-1">
                {d?.recent_activity.map((log) => (
                  <li key={log.id} className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50">
                    <div className="min-w-0">
                      <span className="block truncate text-xs font-medium">
                        {log.action.replaceAll("_", " ").toLowerCase()}
                      </span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {log.user_email ?? "system"}
                        {log.entity_type ? ` · ${log.entity_type}` : ""}
                      </span>
                    </div>
                    <span className="shrink-0 text-[11px] text-muted-foreground">{timeAgo(log.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm font-semibold">Recent payout batches</CardTitle>
          <Link href="/payout-batches" className="text-xs font-medium text-primary hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} cols={6} />
          ) : (d?.recent_batches.length ?? 0) === 0 ? (
            <EmptyState icon={CalendarClock} title="No payout batches yet"
                        description="Generate the first weekly batch from the Payout Batches page." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Creators</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Fees</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d?.recent_batches.map((b) => (
                  <TableRow key={b.id} className="cursor-pointer" onClick={() => router.push(`/payout-batches/${b.id}`)}>
                    <TableCell className="font-medium">{periodLabel(b.period_start, b.period_end)}</TableCell>
                    <TableCell className="text-right tnum">{b.creator_count}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(b.gross_amount)}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(b.platform_fee)}</TableCell>
                    <TableCell className="text-right tnum font-medium">{formatMoney(b.net_amount)}</TableCell>
                    <TableCell><StatusBadge status={b.status} /></TableCell>
                    <TableCell className="text-muted-foreground">{timeAgo(b.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CreatorDashboardView({ name }: { name: string }) {
  const { data, isLoading, isError, error, refetch } =
    useQuery({
      queryKey: ["dashboard", "creator"],
      queryFn: () => api.get<ApiEnvelope<CreatorDashboard>>("/dashboard/creator/"),
    });

  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const d = data?.data;
  const cards = d?.cards;

  return (
    <div>
      <PageHeader title={`Hello, ${name.split(" ")[0]}`}
                  description="Your earnings and payout activity." />

      {isLoading || !cards ? (
        <CardsSkeleton count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Current Earnings" value={formatMoney(cards.current_earnings)}
                    hint={`${cards.current_earnings_count} job(s) awaiting next batch`} icon={Coins} />
          <StatCard label="Pending Payout" value={formatMoney(cards.pending_payout)} accent="warning"
                    hint={`${cards.pending_payout_count} payout(s) in processing`} icon={Wallet} />
          <StatCard label="Paid This Month" value={formatMoney(cards.paid_this_month)} accent="success"
                    icon={Banknote} />
          <StatCard label="Total Earnings" value={formatMoney(cards.total_earnings)}
                    hint={`Lifetime net of ${formatMoney(cards.total_gross)} gross`} icon={CircleDollarSign} />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-semibold">Recent jobs</CardTitle>
            <Link href="/jobs" className="text-xs font-medium text-primary hover:underline">View all</Link>
          </CardHeader>
          <CardContent>
            {isLoading ? <TableSkeleton rows={4} cols={4} /> : (d?.recent_jobs.length ?? 0) === 0 ? (
              <EmptyState title="No jobs yet" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Job</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d?.recent_jobs.map((j) => (
                    <TableRow key={j.id}>
                      <TableCell className="max-w-[220px] truncate font-medium">{j.title}</TableCell>
                      <TableCell><StatusBadge status={j.status} /></TableCell>
                      <TableCell className="text-right tnum">{j.earning_net ? formatMoney(j.earning_net) : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-semibold">Recent payouts</CardTitle>
            <Link href="/payouts" className="text-xs font-medium text-primary hover:underline">View all</Link>
          </CardHeader>
          <CardContent>
            {isLoading ? <TableSkeleton rows={4} cols={4} /> : (d?.recent_payouts.length ?? 0) === 0 ? (
              <EmptyState icon={ArrowDownRight} title="No payouts yet"
                          description="Payouts appear here after the weekly batch runs." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Paid</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d?.recent_payouts.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium">{periodLabel(p.period_start, p.period_end)}</TableCell>
                      <TableCell className="text-right tnum">{formatMoney(p.net_amount)}</TableCell>
                      <TableCell><StatusBadge status={p.status} /></TableCell>
                      <TableCell className="text-muted-foreground">{p.processed_at ? formatDateTime(p.processed_at) : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

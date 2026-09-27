"use client";

import { useQuery } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, NoResultsState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CreatorPayout, Paged } from "@/lib/types";
import { formatDateTime, formatMoney, periodLabel } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function PayoutsPage() {
  const { isAdmin } = useAuth();
  const [page, setPage] = React.useState(1);
  const [status, setStatus] = React.useState("");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["payouts", page, status],
    queryFn: () =>
      api.get<Paged<CreatorPayout>>("/payouts/", {
        page, page_size: PAGE_SIZE, status: status || undefined,
      }),
  });

  return (
    <div>
      <PageHeader title={isAdmin ? "Payouts" : "My payouts"}
                  description={isAdmin
                    ? "Every creator payout across all batches."
                    : "Your payout history — one record per weekly batch you were included in."} />

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <Select value={status || "all"} onValueChange={(v) => { setStatus(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="PROCESSING">Processing</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={8} cols={7} />
        ) : (data?.count ?? 0) === 0 ? (
          status ? (
            <NoResultsState onReset={() => setStatus("")} />
          ) : (
            <EmptyState icon={Wallet} title="No payouts yet"
                        description="Payouts appear after the weekly batch is generated and processed." />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  {isAdmin && <TableHead>Creator</TableHead>}
                  <TableHead className="text-right">Earnings</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Paid date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="whitespace-nowrap">
                      {isAdmin ? (
                        <Link href={`/payout-batches/${p.payout_batch}`} className="font-medium hover:text-primary">
                          {periodLabel(p.period_start, p.period_end)}
                        </Link>
                      ) : (
                        <span className="font-medium">{periodLabel(p.period_start, p.period_end)}</span>
                      )}
                    </TableCell>
                    {isAdmin && (
                      <TableCell>
                        <Link href={`/creators/${p.creator}`} className="text-muted-foreground hover:text-primary">
                          {p.creator_name}
                        </Link>
                      </TableCell>
                    )}
                    <TableCell className="text-right tnum">{p.earning_count}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(p.gross_amount)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">−{formatMoney(p.platform_fee)}</TableCell>
                    <TableCell className="text-right tnum font-semibold">{formatMoney(p.net_amount)}</TableCell>
                    <TableCell>
                      <StatusBadge status={p.status} />
                      {p.failure_reason && (
                        <div className="mt-0.5 max-w-[220px] truncate text-[11px] text-destructive" title={p.failure_reason}>
                          {p.failure_reason}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(p.processed_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={data!.page} totalPages={data!.total_pages} count={data!.count}
                        pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, NoResultsState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { Paged, PayoutBatch } from "@/lib/types";
import { formatMoney, periodLabel, timeAgo } from "@/lib/utils";

const PAGE_SIZE = 20;

interface NextPeriod { period_start: string; period_end: string; already_generated: boolean }

export default function PayoutBatchesPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toast } = useToast();

  const [page, setPage] = React.useState(1);
  const [status, setStatus] = React.useState("");
  const [generateOpen, setGenerateOpen] = React.useState(false);
  const [customStart, setCustomStart] = React.useState("");
  const [customEnd, setCustomEnd] = React.useState("");
  const [useCustom, setUseCustom] = React.useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["payout-batches", page, status],
    queryFn: () =>
      api.get<Paged<PayoutBatch>>("/payout-batches/", {
        page, page_size: PAGE_SIZE, status: status || undefined,
      }),
  });

  const { data: nextPeriod, refetch: refetchNext } = useQuery({
    queryKey: ["payout-batches", "next-period"],
    queryFn: () =>
      api.get<{ success: boolean; data: NextPeriod }>("/payout-batches/next-period/").then((r) => r.data),
    enabled: generateOpen,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      api.post<PayoutBatch>(
        "/payout-batches/generate/",
        useCustom && customStart && customEnd
          ? { period_start: customStart, period_end: customEnd }
          : {}
      ),
    onSuccess: (batch) => {
      toast({
        title: "Payout batch generated",
        description: `${batch.creator_count} creator(s) · net ${formatMoney(batch.net_amount)}`,
        variant: "success",
      });
      setGenerateOpen(false);
      qc.invalidateQueries({ queryKey: ["payout-batches"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      router.push(`/payout-batches/${batch.id}`);
    },
    onError: (e) =>
      toast({
        title: "Generation failed",
        description: e instanceof ApiError ? `${e.message} (${e.code})` : undefined,
        variant: "error",
      }),
  });

  return (
    <div>
      <PageHeader title="Payout batches"
                  description="Weekly payout runs. Generation is transaction-safe and duplicate-proof.">
        <Button onClick={() => { setGenerateOpen(true); setUseCustom(false); refetchNext(); }}>
          <Zap /> Generate batch
        </Button>
      </PageHeader>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <Select value={status || "all"} onValueChange={(v) => { setStatus(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="DRAFT">Draft</SelectItem>
            <SelectItem value="READY">Ready</SelectItem>
            <SelectItem value="PROCESSING">Processing</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={6} cols={7} />
        ) : (data?.count ?? 0) === 0 ? (
          status ? (
            <NoResultsState onReset={() => setStatus("")} />
          ) : (
            <EmptyState icon={CalendarClock} title="No payout batches yet"
                        description="Generate the weekly batch to include all eligible pending earnings."
                        action={<Button size="sm" onClick={() => setGenerateOpen(true)}><Zap /> Generate batch</Button>} />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Creators</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Fees</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Rule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((b) => (
                  <TableRow key={b.id} className="cursor-pointer" onClick={() => router.push(`/payout-batches/${b.id}`)}>
                    <TableCell className="whitespace-nowrap font-medium">{periodLabel(b.period_start, b.period_end)}</TableCell>
                    <TableCell className="text-right tnum">{b.creator_count}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(b.gross_amount)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">{formatMoney(b.platform_fee)}</TableCell>
                    <TableCell className="text-right tnum font-semibold">{formatMoney(b.net_amount)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {b.rule_name ? `${b.rule_name} · ${b.fee_percentage}%` : "—"}
                    </TableCell>
                    <TableCell><StatusBadge status={b.status} /></TableCell>
                    <TableCell className="text-muted-foreground">{timeAgo(b.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={data!.page} totalPages={data!.total_pages} count={data!.count}
                        pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      <ConfirmDialog
        open={generateOpen} onOpenChange={setGenerateOpen}
        title="Generate payout batch"
        confirmLabel="Generate" busy={generateMutation.isPending}
        onConfirm={() => generateMutation.mutate()}
      >
        {nextPeriod && !useCustom ? (
          nextPeriod.already_generated ? (
            <Alert variant="warning">
              <AlertDescription>
                A batch for {periodLabel(nextPeriod.period_start, nextPeriod.period_end)} already
                exists. Generating again will be rejected (duplicate protection). You can pick a
                different period below.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="rounded-md border bg-muted/40 px-4 py-3 text-sm">
              <p className="font-medium">Period: {periodLabel(nextPeriod.period_start, nextPeriod.period_end)}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Includes every pending earning from completed jobs up to the end of the period —
                earnings below the minimum payout roll over to the next batch.
              </p>
            </div>
          )
        ) : null}

        <div className="space-y-3 rounded-md border px-4 py-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useCustom}
              onChange={(e) => setUseCustom(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-[hsl(var(--primary))]"
            />
            Use a custom period
          </label>
          {useCustom && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="gp-start" className="text-xs text-muted-foreground">Period start</label>
                <input id="gp-start" type="date" value={customStart}
                       onChange={(e) => setCustomStart(e.target.value)}
                       className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </div>
              <div className="space-y-1">
                <label htmlFor="gp-end" className="text-xs text-muted-foreground">Period end</label>
                <input id="gp-end" type="date" value={customEnd}
                       onChange={(e) => setCustomEnd(e.target.value)}
                       className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </div>
              <p className="col-span-2 text-[11px] text-muted-foreground">
                The period end cannot be in the future. Jobs completed today become payable with a
                period that covers today (e.g. the current Mon–Sun week).
              </p>
            </div>
          )}
        </div>
      </ConfirmDialog>
    </div>
  );
}

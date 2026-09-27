"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleAlert, Play } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ErrorState, TableSkeleton } from "@/components/shared/states";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { PayoutBatch } from "@/lib/types";
import { formatDateTime, formatMoney, periodLabel } from "@/lib/utils";

export default function PayoutBatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [processOpen, setProcessOpen] = React.useState(false);

  const { data: batch, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["payout-batch", id],
    queryFn: () => api.get<PayoutBatch>(`/payout-batches/${id}/`),
  });

  const processMutation = useMutation({
    mutationFn: () => api.post<PayoutBatch>(`/payout-batches/${id}/process/`, {}),
    onSuccess: (result) => {
      toast({
        title: "Batch processed",
        description: `${result.paid_count} paid · ${result.failed_count} failed (simulated)`,
        variant: result.failed_count ? "warning" : "success",
      });
      setProcessOpen(false);
      qc.invalidateQueries({ queryKey: ["payout-batch", id] });
      qc.invalidateQueries({ queryKey: ["payout-batches"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["payouts"] });
    },
    onError: (e) =>
      toast({
        title: "Processing failed",
        description: e instanceof ApiError ? `${e.message} (${e.code})` : undefined,
        variant: "error",
      }),
  });

  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const canProcess = batch && (batch.status === "READY" || batch.status === "FAILED");
  const failedPayouts = batch?.payouts?.filter((p) => p.status === "FAILED") ?? [];

  return (
    <div>
      <Link href="/payout-batches" className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to batches
      </Link>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            {batch ? periodLabel(batch.period_start, batch.period_end) : "Payout batch"}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {batch && <StatusBadge status={batch.status} />}
            {batch && <span>Created {formatDateTime(batch.created_at)}</span>}
            {batch?.processed_at && <span>· Processed {formatDateTime(batch.processed_at)}</span>}
          </p>
        </div>
        {canProcess && (
          <Button onClick={() => setProcessOpen(true)}>
            <Play /> Process batch
          </Button>
        )}
      </div>

      {!isLoading && (batch?.status === "FAILED" || failedPayouts.length > 0) && (
        <Alert variant="warning" className="mb-6">
          <CircleAlert />
          <AlertDescription>
            {failedPayouts.length} payout(s) failed during simulated processing. Their earnings were
            released back to pending and will roll into the next batch.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Creators" value={batch?.creator_count ?? 0} loading={isLoading} />
        <StatCard label="Gross" value={formatMoney(batch?.gross_amount)} loading={isLoading} />
        <StatCard label="Platform fees" value={formatMoney(batch?.platform_fee)} loading={isLoading} />
        <StatCard label="Net payout" value={formatMoney(batch?.net_amount)} accent="success" loading={isLoading} />
      </div>

      {batch?.payout_rule_snapshot && Object.keys(batch.payout_rule_snapshot).length > 0 && (
        <div className="mt-4 rounded-lg border bg-muted/30 px-4 py-3 text-xs text-muted-foreground">
          Rule snapshot: <span className="font-medium text-foreground">{String(batch.payout_rule_snapshot.name)}</span>
          {" · "}fee {String(batch.payout_rule_snapshot.platform_fee_percentage)}%
          {" · "}minimum {formatMoney(String(batch.payout_rule_snapshot.minimum_payout))}
          {" · "}{String(batch.payout_rule_snapshot.payout_frequency).toLowerCase()}
          <span className="ml-2 hidden sm:inline">(historical payouts never change when rules are edited)</span>
        </div>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Creator payouts ({batch?.payouts?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={6} cols={7} />
          ) : (batch?.payouts?.length ?? 0) === 0 ? (
            <p className="px-2 py-8 text-center text-sm text-muted-foreground">
              No payouts in this batch — no creators met the minimum threshold for the period.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Creator</TableHead>
                  <TableHead className="text-right">Earnings</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                  <TableHead className="text-right">Adj.</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Processed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batch?.payouts?.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <Link href={`/creators/${p.creator}`} className="font-medium hover:text-primary">
                        {p.creator_name}
                      </Link>
                      {p.failure_reason && (
                        <div className="max-w-[260px] truncate text-xs text-destructive" title={p.failure_reason}>
                          {p.failure_reason}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right tnum">{p.earning_count}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(p.gross_amount)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">−{formatMoney(p.platform_fee)}</TableCell>
                    <TableCell className={`text-right tnum ${parseFloat(p.adjustments) !== 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {parseFloat(p.adjustments) === 0 ? "—" : formatMoney(p.adjustments, { sign: true })}
                    </TableCell>
                    <TableCell className="text-right tnum font-semibold">{formatMoney(p.net_amount)}</TableCell>
                    <TableCell><StatusBadge status={p.status} /></TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(p.processed_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={processOpen} onOpenChange={setProcessOpen}
        title="Process this payout batch?"
        description={`Simulated transfers for ${batch?.creator_count ?? 0} creator(s), net ${formatMoney(batch?.net_amount)}. Some transfers may fail randomly to demonstrate failure handling — failed earnings roll over to the next batch.`}
        confirmLabel="Process payouts" busy={processMutation.isPending}
        onConfirm={() => processMutation.mutate()}
      />
    </div>
  );
}

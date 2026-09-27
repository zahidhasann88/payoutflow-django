"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleCheckBig } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ErrorState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Earning, Job } from "@/lib/types";
import { formatDateTime, formatMoney } from "@/lib/utils";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { toast } = useToast();
  const { isAdmin } = useAuth();
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  const { data: job, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.get<Job>(`/jobs/${id}/`),
  });

  const { data: earningData } = useQuery({
    queryKey: ["earnings", "job", id],
    queryFn: async () => {
      const res = await api.get<{ success: boolean; count: number; results: Earning[] }>(
        "/earnings/", { job: id, page_size: 1 }
      );
      return res.results[0] ?? null;
    },
    enabled: !!job && job.status === "COMPLETED",
  });

  const completeMutation = useMutation({
    mutationFn: () => api.post<Job>(`/jobs/${id}/complete/`, {}),
    onSuccess: () => {
      toast({ title: "Job completed", description: "Earnings calculated.", variant: "success" });
      setConfirmOpen(false);
      qc.invalidateQueries({ queryKey: ["job", id] });
      qc.invalidateQueries({ queryKey: ["earnings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) =>
      toast({ title: "Could not complete job", description: e instanceof ApiError ? e.message : undefined, variant: "error" }),
  });

  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const canComplete = isAdmin && job && (job.status === "PENDING" || job.status === "IN_PROGRESS");

  return (
    <div>
      <Link href="/jobs" className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to jobs
      </Link>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          {isLoading ? <Skeleton className="h-7 w-64" /> : (
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{job?.title}</h1>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {job && <StatusBadge status={job.status} />}
            <span>{job?.creator_name}</span>
            <span>·</span>
            <span>Created {formatDateTime(job?.created_at)}</span>
            {job?.completed_at && (<><span>·</span><span>Completed {formatDateTime(job.completed_at)}</span></>)}
          </div>
        </div>
        {canComplete && (
          <Button onClick={() => setConfirmOpen(true)}>
            <CircleCheckBig /> Mark completed
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm font-semibold">Job details</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {isLoading ? (
              <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : (
              <>
                <Row label="Base amount" value={formatMoney(job?.base_amount)} />
                <Row label="Surge multiplier" value={`× ${parseFloat(job?.surge_multiplier ?? "1").toFixed(2)}`} />
                <Row label="Tips" value={formatMoney(job?.tip_amount)} />
                <Separator />
                <div>
                  <p className="mb-1 text-xs text-muted-foreground">Description</p>
                  <p className="whitespace-pre-wrap text-sm text-foreground/90">{job?.description || "No description provided."}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Earnings breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {job?.status !== "COMPLETED" ? (
              <p className="rounded-md border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                Earnings are calculated when the job is completed.
              </p>
            ) : !earningData ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <div className="space-y-2.5 text-sm">
                <Row label="Base earnings" value={formatMoney(earningData.base_amount)} />
                <Row label={`Surge bonus (×${(parseFloat(earningData.base_amount) > 0 ? (parseFloat(earningData.surge_amount) / parseFloat(earningData.base_amount)) : 1).toFixed(2)})`}
                     value={formatMoney(earningData.surge_amount, { sign: true })} accent="text-success" />
                <Row label="Tips" value={formatMoney(earningData.tip_amount, { sign: true })} accent="text-success" />
                <Separator />
                <Row label="Gross earnings" value={formatMoney(earningData.gross_amount)} strong />
                <Row label={`Platform fee (${parseFloat(earningData.fee_percentage_applied)}%)`}
                     value={`−${formatMoney(earningData.platform_fee)}`} accent="text-destructive" />
                <Row label="Adjustments"
                     value={`${parseFloat(earningData.adjustment_amount) === 0 ? "" : formatMoney(earningData.adjustment_amount, { sign: true })}`}
                     accent={parseFloat(earningData.adjustment_amount) < 0 ? "text-destructive" : undefined} />
                <Separator />
                <Row label="Net payout" value={formatMoney(earningData.net_amount)} strong large />
                <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
                  <span>Payout status</span>
                  <StatusBadge status={earningData.payout_status} />
                </div>
                {earningData.adjustments.length > 0 && (
                  <div className="rounded-md bg-muted/50 p-3">
                    <p className="mb-1.5 text-xs font-medium">Adjustment history</p>
                    {earningData.adjustments.map((a) => (
                      <div key={a.id} className="flex justify-between py-0.5 text-xs">
                        <span className="text-muted-foreground">{a.reason}</span>
                        <span className="tnum font-medium">{formatMoney(a.amount, { sign: true })}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={confirmOpen} onOpenChange={setConfirmOpen}
        title={`Complete “${job?.title}”?`}
        description="Earnings will be calculated with the active payout rule and become eligible for the next weekly batch."
        confirmLabel="Complete job" busy={completeMutation.isPending}
        onConfirm={() => completeMutation.mutate()}
      />
    </div>
  );
}

function Row({ label, value, strong, large, accent }: {
  label: string; value: React.ReactNode; strong?: boolean; large?: boolean; accent?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`tnum ${strong ? "font-semibold" : "font-medium"} ${large ? "text-lg" : ""} ${accent ?? ""}`}>
        {value || "—"}
      </span>
    </div>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle, Scale } from "lucide-react";
import * as React from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState, NoResultsState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Earning, Paged } from "@/lib/types";
import { formatDateTime, formatMoney } from "@/lib/utils";

const PAGE_SIZE = 20;

const adjustmentSchema = z.object({
  amount: z.coerce.number({ invalid_type_error: "Required" }).refine((n) => n !== 0, "Amount must not be zero"),
  reason: z.string().min(3, "Give a short reason").max(255),
});

export default function EarningsPage() {
  const qc = useQueryClient();
  const { isAdmin } = useAuth();

  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [adjustTarget, setAdjustTarget] = React.useState<Earning | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["earnings", page, search, status],
    queryFn: () =>
      api.get<Paged<Earning>>("/earnings/", {
        page, page_size: PAGE_SIZE,
        search: search || undefined,
        payout_status: status || undefined,
      }),
  });

  const filtered = search || status;

  return (
    <div>
      <PageHeader title="Earnings"
                  description={isAdmin
                    ? "Every earning calculated from completed jobs (Decimal math, fee captured at completion)."
                    : "Earnings from your completed jobs."} />

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search by job title…" />
        <Select value={status || "all"} onValueChange={(v) => { setStatus(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All payout statuses</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="INCLUDED">In batch</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={8} cols={8} />
        ) : (data?.count ?? 0) === 0 ? (
          filtered ? (
            <NoResultsState onReset={() => { setSearch(""); setStatus(""); }} />
          ) : (
            <EmptyState icon={Scale} title="No earnings yet"
                        description="Complete a job and the engine calculates its earning automatically." />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  {isAdmin && <TableHead>Creator</TableHead>}
                  <TableHead className="text-right">Base</TableHead>
                  <TableHead className="text-right">Surge</TableHead>
                  <TableHead className="text-right">Tips</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                  <TableHead className="text-right">Adj.</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Calculated</TableHead>
                  {isAdmin && <TableHead className="w-24" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="max-w-[200px] truncate font-medium">{e.job_title}</TableCell>
                    {isAdmin && <TableCell className="text-muted-foreground">{e.creator_name}</TableCell>}
                    <TableCell className="text-right tnum">{formatMoney(e.base_amount)}</TableCell>
                    <TableCell className="text-right tnum text-success">+{formatMoney(e.surge_amount)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">+{formatMoney(e.tip_amount)}</TableCell>
                    <TableCell className="text-right tnum">{formatMoney(e.gross_amount)}</TableCell>
                    <TableCell className="text-right tnum text-destructive">−{formatMoney(e.platform_fee)}</TableCell>
                    <TableCell className={`text-right tnum ${parseFloat(e.adjustment_amount) < 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {parseFloat(e.adjustment_amount) === 0 ? "—" : formatMoney(e.adjustment_amount, { sign: true })}
                    </TableCell>
                    <TableCell className="text-right tnum font-semibold">{formatMoney(e.net_amount)}</TableCell>
                    <TableCell><StatusBadge status={e.payout_status} /></TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(e.created_at)}</TableCell>
                    {isAdmin && (
                      <TableCell>
                        <Button variant="ghost" size="sm" disabled={e.payout_status !== "PENDING"}
                                onClick={() => setAdjustTarget(e)}>
                          <Scale className="h-3.5 w-3.5" /> Adjust
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={data!.page} totalPages={data!.total_pages} count={data!.count}
                        pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      <AdjustmentDialog
        key={adjustTarget?.id ?? "none"}
        earning={adjustTarget}
        onOpenChange={(o) => !o && setAdjustTarget(null)}
        onDone={() => {
          setAdjustTarget(null);
          qc.invalidateQueries({ queryKey: ["earnings"] });
          qc.invalidateQueries({ queryKey: ["dashboard"] });
        }}
      />
    </div>
  );
}

function AdjustmentDialog({ earning, onOpenChange, onDone }: {
  earning: Earning | null;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const { toast } = useToast();
  const [apiError, setApiError] = React.useState<string | null>(null);

  const form = useForm<z.infer<typeof adjustmentSchema>>({
    resolver: zodResolver(adjustmentSchema),
    defaultValues: { amount: 0, reason: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: z.infer<typeof adjustmentSchema>) =>
      api.post(`/earnings/${earning!.id}/adjustments/`, {
        amount: values.amount.toFixed(2),
        reason: values.reason,
      }),
    onSuccess: () => {
      toast({ title: "Adjustment applied", description: "Net earnings recalculated.", variant: "success" });
      onDone();
    },
    onError: (e) => setApiError(e instanceof ApiError ? `${e.message} (${e.code})` : "Failed to apply adjustment."),
  });

  const previewAmount = useWatch({ control: form.control, name: "amount" });
  const previewNet = earning
    ? parseFloat(earning.net_amount) + (Number.isFinite(previewAmount) ? previewAmount : 0)
    : 0;

  return (
    <Dialog open={!!earning} onOpenChange={(o) => !mutation.isPending && onOpenChange(o)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add adjustment</DialogTitle>
          <DialogDescription>
            {earning ? `“${earning.job_title}” — current net ${formatMoney(earning.net_amount)}. Negative values deduct.` : ""}
          </DialogDescription>
        </DialogHeader>

        {apiError && (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">{apiError}</p>
        )}

        <form className="space-y-4" onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
          <div className="space-y-1.5">
            <Label htmlFor="adj-amount">Amount ($)</Label>
            <Input id="adj-amount" type="number" step="0.01" placeholder="-5.00" {...form.register("amount")} />
            {form.formState.errors.amount && (
              <p className="text-xs text-destructive">{form.formState.errors.amount.message}</p>
            )}
            <p className="text-xs text-muted-foreground tnum">
              New net: <span className={previewNet < 0 ? "font-medium text-destructive" : "font-medium"}>{formatMoney(previewNet)}</span>
              {previewNet < 0 && " — negative net amounts are rejected"}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="adj-reason">Reason</Label>
            <Textarea id="adj-reason" placeholder="e.g. Partial refund to client" {...form.register("reason")} />
            {form.formState.errors.reason && (
              <p className="text-xs text-destructive">{form.formState.errors.reason.message}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Apply adjustment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

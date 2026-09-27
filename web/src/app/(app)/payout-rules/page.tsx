"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Check, LoaderCircle, Plus, Power, Settings } from "lucide-react";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { PayoutRule, Paged } from "@/lib/types";
import { formatDateTime, formatMoney } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(3, "Name is required").max(120),
  platform_fee_percentage: z.coerce.number({ invalid_type_error: "Required" }).min(0).max(100, "Max 100%"),
  minimum_payout: z.coerce.number().min(0),
});

type RuleFormValues = z.infer<typeof schema>;

export default function PayoutRulesPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [formOpen, setFormOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<PayoutRule | null>(null);
  const [activateTarget, setActivateTarget] = React.useState<PayoutRule | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["payout-rules"],
    queryFn: () => api.get<Paged<PayoutRule>>("/payout-rules/", { page_size: 50, ordering: "-created_at" }),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["payout-rules"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const saveMutation = useMutation({
    mutationFn: ({ id, values }: { id?: number; values: RuleFormValues }) =>
      id
        ? api.patch<PayoutRule>(`/payout-rules/${id}/`, values)
        : api.post<PayoutRule>("/payout-rules/", { ...values, payout_frequency: "WEEKLY", is_active: false }),
    onSuccess: () => {
      toast({ title: editTarget ? "Rule updated" : "Rule created", variant: "success" });
      setFormOpen(false); setEditTarget(null); setFormError(null); invalidate();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Failed to save rule."),
  });

  const activateMutation = useMutation({
    mutationFn: (rule: PayoutRule) => api.patch<PayoutRule>(`/payout-rules/${rule.id}/`, { is_active: true }),
    onSuccess: () => {
      toast({ title: "Rule activated", description: "Applies to new earnings and future batches — history is untouched.", variant: "success" });
      setActivateTarget(null); invalidate();
    },
    onError: (e) =>
      toast({ title: "Activation failed", description: e instanceof ApiError ? e.message : undefined, variant: "error" }),
  });

  const active = data?.results.find((r) => r.is_active);

  return (
    <div>
      <PageHeader title="Payout rules"
                  description="Platform fee, minimum payout and frequency. Exactly one rule is active; batches snapshot the rule they used.">
        <Button onClick={() => { setEditTarget(null); setFormError(null); setFormOpen(true); }}>
          <Plus /> New rule
        </Button>
      </PageHeader>

      {active && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-primary/25 bg-accent px-4 py-3 text-sm">
          <Check className="h-4 w-4 text-primary" />
          <span>
            Active: <strong>{active.name}</strong> — {parseFloat(active.platform_fee_percentage)}% platform fee,
            minimum {formatMoney(active.minimum_payout)}, weekly
          </span>
        </div>
      )}

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={4} cols={6} />
        ) : (data?.count ?? 0) === 0 ? (
          <EmptyState icon={Settings} title="No payout rules"
                      description="Create a rule (e.g. 10% fee, $20 minimum) before generating payouts."
                      action={<Button size="sm" onClick={() => setFormOpen(true)}><Plus /> New rule</Button>} />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Platform fee</TableHead>
                <TableHead className="text-right">Minimum payout</TableHead>
                <TableHead>Frequency</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-32" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-right tnum">{parseFloat(r.platform_fee_percentage).toFixed(2)}%</TableCell>
                  <TableCell className="text-right tnum">{formatMoney(r.minimum_payout)}</TableCell>
                  <TableCell><Badge variant="secondary">Weekly</Badge></TableCell>
                  <TableCell>{r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="muted">Inactive</Badge>}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(r.updated_at)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {!r.is_active && (
                        <Button variant="ghost" size="sm" onClick={() => setActivateTarget(r)}>
                          <Power className="h-3.5 w-3.5" /> Activate
                        </Button>
                      )}
                      <Button variant="ghost" size="sm"
                              onClick={() => { setEditTarget(r); setFormError(null); setFormOpen(true); }}>
                        Edit
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <RuleDialog
        open={formOpen}
        onOpenChange={(o) => { setFormOpen(o); if (!o) setEditTarget(null); }}
        rule={editTarget}
        busy={saveMutation.isPending}
        formError={formError}
        onSubmit={(values) => saveMutation.mutate({ id: editTarget?.id, values })}
      />

      <ConfirmDialog
        open={!!activateTarget} onOpenChange={(o) => !o && setActivateTarget(null)}
        title={`Activate “${activateTarget?.name}”?`}
        description="The currently active rule will be deactivated. New earnings use this fee; historical payouts keep their snapshots."
        confirmLabel="Activate rule" busy={activateMutation.isPending}
        onConfirm={() => { if (activateTarget) activateMutation.mutate(activateTarget); }}
      />
    </div>
  );
}

function RuleDialog({ open, onOpenChange, rule, busy, onSubmit, formError }: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  rule: PayoutRule | null;
  busy?: boolean;
  onSubmit: (values: RuleFormValues) => void;
  formError?: string | null;
}) {
  const form = useForm<RuleFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", platform_fee_percentage: 10, minimum_payout: 20 },
  });

  React.useEffect(() => {
    if (open) {
      form.reset(rule ? {
        name: rule.name,
        platform_fee_percentage: parseFloat(rule.platform_fee_percentage),
        minimum_payout: parseFloat(rule.minimum_payout),
      } : { name: "", platform_fee_percentage: 10, minimum_payout: 20 });
    }
  }, [open, rule, form]);

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{rule ? "Edit rule" : "New payout rule"}</DialogTitle>
          <DialogDescription>Weekly frequency only — the engine pays out once per week (Mon–Sun periods).</DialogDescription>
        </DialogHeader>
        {formError && (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">{formError}</p>
        )}
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-1.5">
            <Label htmlFor="pr-name">Name</Label>
            <Input id="pr-name" placeholder="Standard Weekly 10%" {...form.register("name")} />
            {form.formState.errors.name && <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="pr-fee">Platform fee (%)</Label>
              <Input id="pr-fee" type="number" step="0.01" min="0" max="100" {...form.register("platform_fee_percentage")} />
              {form.formState.errors.platform_fee_percentage && (
                <p className="text-xs text-destructive">{form.formState.errors.platform_fee_percentage.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pr-min">Minimum payout ($)</Label>
              <Input id="pr-min" type="number" step="0.01" min="0" {...form.register("minimum_payout")} />
              {form.formState.errors.minimum_payout && (
                <p className="text-xs text-destructive">{form.formState.errors.minimum_payout.message}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
            <Button type="submit" disabled={busy}>
              {busy && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {rule ? "Save changes" : "Create rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { CreatorProfile, Job, Paged } from "@/lib/types";

const schema = z.object({
  creator: z.coerce.number({ invalid_type_error: "Select a creator" }).positive("Select a creator"),
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  description: z.string().max(2000).optional().or(z.literal("")),
  base_amount: z.coerce.number({ invalid_type_error: "Required" }).min(0, "Cannot be negative").max(9_999_999),
  surge_multiplier: z.coerce.number().min(1, "Minimum is 1.00").max(10, "Maximum is 10.00"),
  tip_amount: z.coerce.number().min(0, "Cannot be negative"),
});

export type JobFormValues = z.infer<typeof schema>;

export function JobFormDialog({
  open, onOpenChange, job, busy, onSubmit, formError,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job?: Job | null;
  busy?: boolean;
  onSubmit: (values: JobFormValues) => void;
  formError?: string | null;
}) {
  const { data: creators } = useQuery({
    queryKey: ["creators", "all-simple"],
    queryFn: () => api.get<Paged<CreatorProfile>>("/creators/", { page_size: 100 }),
    enabled: open,
  });

  const form = useForm<JobFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      creator: 0, title: "", description: "",
      base_amount: 100, surge_multiplier: 1, tip_amount: 0,
    },
  });

  const creatorValue = useWatch({ control: form.control, name: "creator" });

  useEffect(() => {
    if (open) {
      form.reset({
        creator: job?.creator ?? 0,
        title: job?.title ?? "",
        description: job?.description ?? "",
        base_amount: job ? parseFloat(job.base_amount) : 100,
        surge_multiplier: job ? parseFloat(job.surge_multiplier) : 1,
        tip_amount: job ? parseFloat(job.tip_amount) : 0,
      });
    }
  }, [open, job, form]);

  const moneyLocked = job?.status === "COMPLETED";

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{job ? "Edit job" : "New job"}</DialogTitle>
          <DialogDescription>
            {job
              ? "Money fields are locked once a job is completed."
              : "Jobs generate earnings when they are completed."}
          </DialogDescription>
        </DialogHeader>

        {formError && (
          <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {formError}
          </p>
        )}

        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-1.5">
            <Label>Creator</Label>
            <Select
              value={creatorValue ? String(creatorValue) : undefined}
              onValueChange={(v) => form.setValue("creator", Number(v), { shouldValidate: true })}
              disabled={!!job}
            >
              <SelectTrigger><SelectValue placeholder="Select creator…" /></SelectTrigger>
              <SelectContent>
                {creators?.results.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.display_name} · {c.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.creator && (
              <p className="text-xs text-destructive">{form.formState.errors.creator.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="jf-title">Title</Label>
            <Input id="jf-title" placeholder="Product photography session" {...form.register("title")} />
            {form.formState.errors.title && (
              <p className="text-xs text-destructive">{form.formState.errors.title.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="jf-desc">Description</Label>
            <Textarea id="jf-desc" placeholder="Optional details…" {...form.register("description")} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="jf-base">Base ($)</Label>
              <Input id="jf-base" type="number" step="0.01" min="0" disabled={moneyLocked} {...form.register("base_amount")} />
              {form.formState.errors.base_amount && (
                <p className="text-xs text-destructive">{form.formState.errors.base_amount.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="jf-surge">Surge ×</Label>
              <Input id="jf-surge" type="number" step="0.01" min="1" max="10" disabled={moneyLocked} {...form.register("surge_multiplier")} />
              {form.formState.errors.surge_multiplier && (
                <p className="text-xs text-destructive">{form.formState.errors.surge_multiplier.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="jf-tip">Tips ($)</Label>
              <Input id="jf-tip" type="number" step="0.01" min="0" disabled={moneyLocked} {...form.register("tip_amount")} />
              {form.formState.errors.tip_amount && (
                <p className="text-xs text-destructive">{form.formState.errors.tip_amount.message}</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
            <Button type="submit" disabled={busy}>
              {busy && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {job ? "Save changes" : "Create job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

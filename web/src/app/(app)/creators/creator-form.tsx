"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { CreatorProfile } from "@/lib/types";

const baseSchema = z.object({
  display_name: z.string().min(2, "Display name is required"),
  phone: z.string().regex(/^\+?[0-9 ()-]{6,20}$/, "Enter a valid phone number").or(z.literal("")),
  payout_method: z.enum(["BANK", "PAYPAL", "OTHER"]),
  payout_account: z.string().max(120),
  tax_status: z.enum(["NOT_SUBMITTED", "SUBMITTED", "VERIFIED"]),
  minimum_payout: z.string().regex(/^\d*(\.\d{0,2})?$/, "Up to 2 decimals").or(z.literal("")),
});

const createSchema = baseSchema.extend({
  email: z.string().email("Enter a valid email"),
  name: z.string().min(2, "Full name is required"),
  password: z.string().min(8, "Minimum 8 characters"),
});

export type CreatorFormValues = z.infer<typeof createSchema>;

interface CreatorFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  creator?: CreatorProfile | null;
  busy?: boolean;
  onSubmit: (values: Partial<CreatorFormValues>) => void;
  formError?: string | null;
}

export function CreatorFormDialog({
  open, onOpenChange, mode, creator, busy, onSubmit, formError,
}: CreatorFormDialogProps) {
  const schema = mode === "create" ? createSchema : baseSchema;
  const form = useForm({
    resolver: zodResolver(schema) as never,
    defaultValues: {
      email: "", name: "", password: "",
      display_name: "", phone: "", payout_method: "BANK",
      payout_account: "", tax_status: "NOT_SUBMITTED", minimum_payout: "",
    },
  });

  const payoutMethod = useWatch({ control: form.control, name: "payout_method" });
  const taxStatus = useWatch({ control: form.control, name: "tax_status" });

  useEffect(() => {
    if (open) {
      form.reset({
        email: creator?.email ?? "",
        name: creator?.name ?? "",
        password: "",
        display_name: creator?.display_name ?? "",
        phone: creator?.phone ?? "",
        payout_method: creator?.payout_method ?? "BANK",
        payout_account: creator?.payout_account ?? "",
        tax_status: creator?.tax_status ?? "NOT_SUBMITTED",
        minimum_payout: creator?.minimum_payout ?? "",
      });
    }
  }, [open, creator, form]);

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "New creator" : "Edit creator"}</DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Creates a login account and payout profile."
              : "Update the payout profile. Changes apply to future payouts."}
          </DialogDescription>
        </DialogHeader>

        {formError && <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">{formError}</p>}

        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={form.handleSubmit((values) => onSubmit(values as Partial<CreatorFormValues>))}
        >
          {mode === "create" && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="cf-email">Email</Label>
                <Input id="cf-email" type="email" placeholder="creator@payoutflow.local" {...form.register("email")} />
                {form.formState.errors.email && <FieldError msg={form.formState.errors.email.message} />}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cf-password">Password</Label>
                <Input id="cf-password" type="password" placeholder="Min. 8 characters" {...form.register("password")} />
                {form.formState.errors.password && <FieldError msg={form.formState.errors.password.message} />}
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="cf-name">Full name</Label>
                <Input id="cf-name" placeholder="Jane Doe" {...form.register("name")} />
                {form.formState.errors.name && <FieldError msg={form.formState.errors.name.message} />}
              </div>
            </>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="cf-display">Display name</Label>
            <Input id="cf-display" placeholder="Jane Creates" {...form.register("display_name")} />
            {form.formState.errors.display_name && <FieldError msg={form.formState.errors.display_name.message} />}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cf-phone">Phone</Label>
            <Input id="cf-phone" placeholder="+1 555 0100" {...form.register("phone")} />
            {form.formState.errors.phone && <FieldError msg={form.formState.errors.phone.message} />}
          </div>

          <div className="space-y-1.5">
            <Label>Payout method</Label>
            <Select value={payoutMethod}
                    onValueChange={(v) => form.setValue("payout_method", v as "BANK" | "PAYPAL" | "OTHER")}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="BANK">Bank transfer</SelectItem>
                <SelectItem value="PAYPAL">PayPal</SelectItem>
                <SelectItem value="OTHER">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cf-account">Payout account</Label>
            <Input id="cf-account" placeholder="Account reference (simulated)" {...form.register("payout_account")} />
          </div>

          <div className="space-y-1.5">
            <Label>Tax status</Label>
            <Select value={taxStatus}
                    onValueChange={(v) => form.setValue("tax_status", v as "NOT_SUBMITTED" | "SUBMITTED" | "VERIFIED")}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="NOT_SUBMITTED">Not submitted</SelectItem>
                <SelectItem value="SUBMITTED">Submitted</SelectItem>
                <SelectItem value="VERIFIED">Verified</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cf-min">Minimum payout (optional override)</Label>
            <Input id="cf-min" inputMode="decimal" placeholder="Rule default" {...form.register("minimum_payout")} />
            {form.formState.errors.minimum_payout && <FieldError msg={form.formState.errors.minimum_payout.message} />}
          </div>

          <div className="sm:col-span-2">
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy}>
                {busy && <LoaderCircle className="h-4 w-4 animate-spin" />}
                {mode === "create" ? "Create creator" : "Save changes"}
              </Button>
            </DialogFooter>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function FieldError({ msg }: { msg?: string }) {
  return msg ? <p className="text-xs text-destructive">{msg}</p> : null;
}

export { Textarea };

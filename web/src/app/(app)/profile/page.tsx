"use client";

import { useMutation } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Landmark, LoaderCircle, Lock, ShieldCheck, UserRound } from "lucide-react";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiEnvelope, CreatorProfile, User } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

const passwordSchema = z.object({
  current_password: z.string().min(1, "Required"),
  new_password: z.string().min(8, "Minimum 8 characters"),
}).refine((d) => d.current_password !== d.new_password, {
  message: "New password must differ from the current one",
  path: ["new_password"],
});

export default function ProfilePage() {
  const { user, isAdmin, refreshUser } = useAuth();
  const { toast } = useToast();

  if (!user) return null;

  return (
    <div>
      <PageHeader title="Profile" description="Your account, payout information and security settings." />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <UserRound className="h-4 w-4 text-muted-foreground" /> Account
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Info label="Name" value={user.name} />
              <Info label="Email" value={user.email} />
              <Info label="Role" value={<Badge2>{isAdmin ? "Administrator" : "Creator"}</Badge2>} />
              <Info label="Status" value={<StatusBadge status={user.status} />} />
              <Info label="Member since" value={formatDate(user.created_at)} />
            </CardContent>
          </Card>

          <PasswordCard onDone={() => { toast({ title: "Password changed", variant: "success" }); refreshUser(); }} />
        </div>

        <div className="space-y-6">
          {user.creator ? <CreatorPayoutInfo creator={user.creator} /> : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <ShieldCheck className="h-4 w-4 text-muted-foreground" /> Platform administration
                </CardTitle>
                <CardDescription>
                  Admin accounts do not have creator payout profiles. Manage creators, jobs,
                  payout rules and weekly batches from the sidebar.
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Badge2({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
      {children}
    </span>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  );
}

function CreatorPayoutInfo({ creator }: { creator: CreatorProfile }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Landmark className="h-4 w-4 text-muted-foreground" /> Payout & tax information
        </CardTitle>
        <CardDescription>
          Where your weekly payouts are sent. This is profile data only — PayoutFlow simulates
          transfers and never connects to real payment providers.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Info label="Display name" value={creator.display_name} />
        <Info label="Phone" value={creator.phone || "—"} />
        <Separator />
        <Info label="Payout method" value={<Badge2>{creator.payout_method}</Badge2>} />
        <Info label="Payout account" value={<span className="font-mono text-xs">{creator.payout_account || "—"}</span>} />
        <Info label="Tax status" value={<StatusBadge status={creator.tax_status} />} />
        <Info label="Minimum payout" value={creator.minimum_payout ? formatMoney(creator.minimum_payout) : "Platform default"} />
        <p className="pt-2 text-xs text-muted-foreground">
          Need a change? Contact platform support — payout details are reviewed by admins for security.
        </p>
      </CardContent>
    </Card>
  );
}

function PasswordCard({ onDone }: { onDone: () => void }) {
  const [apiError, setApiError] = React.useState<string | null>(null);

  const form = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: z.infer<typeof passwordSchema>) =>
      api.patch<ApiEnvelope<User>>("/auth/me/", values),
    onSuccess: () => {
      form.reset();
      setApiError(null);
      onDone();
    },
    onError: (e) =>
      setApiError(e instanceof ApiError ? e.message : "Failed to change password."),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Lock className="h-4 w-4 text-muted-foreground" /> Change password
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
          {apiError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">{apiError}</p>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="pw-current">Current password</Label>
            <Input id="pw-current" type="password" autoComplete="current-password" {...form.register("current_password")} />
            {form.formState.errors.current_password && (
              <p className="text-xs text-destructive">{form.formState.errors.current_password.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pw-new">New password</Label>
            <Input id="pw-new" type="password" autoComplete="new-password" {...form.register("new_password")} />
            {form.formState.errors.new_password && (
              <p className="text-xs text-destructive">{form.formState.errors.new_password.message}</p>
            )}
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}
            Update password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

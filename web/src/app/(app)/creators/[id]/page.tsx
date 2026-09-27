"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Landmark, Mail, Phone, Receipt } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";

import { CreatorFormDialog, type CreatorFormValues } from "../creator-form";
import { ErrorState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { CreatorPayout, CreatorProfile, Earning, Job, Paged } from "@/lib/types";
import { formatDate, formatDateTime, formatMoney, periodLabel } from "@/lib/utils";

export default function CreatorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [editOpen, setEditOpen] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["creator", id],
    queryFn: () => api.get<CreatorProfile>(`/creators/${id}/`),
  });

  const editMutation = useMutation({
    mutationFn: (values: Partial<CreatorFormValues>) =>
      api.patch<CreatorProfile>(`/creators/${id}/`, {
        ...values,
        minimum_payout: values.minimum_payout === "" ? null : values.minimum_payout,
      }),
    onSuccess: () => {
      toast({ title: "Creator updated", variant: "success" });
      setEditOpen(false);
      qc.invalidateQueries({ queryKey: ["creator", id] });
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Update failed."),
  });

  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const creator = data;

  return (
    <div>
      <div className="mb-6">
        <Link href="/creators" className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to creators
        </Link>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {isLoading ? (
              <Skeleton className="h-7 w-48" />
            ) : (
              <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{creator?.display_name}</h1>
            )}
            <p className="mt-1 text-sm text-muted-foreground">{creator?.email}</p>
          </div>
          <div className="flex items-center gap-2">
            {creator && <StatusBadge status={creator.status} />}
            <Button variant="outline" size="sm" onClick={() => { setFormError(null); setEditOpen(true); }}>
              Edit profile
            </Button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle className="text-sm font-semibold">Payout profile</CardTitle></CardHeader>
          <CardContent className="space-y-4 text-sm">
            {isLoading ? (
              <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : (
              <>
                <InfoRow icon={Mail} label="Email" value={creator?.email} />
                <InfoRow icon={Phone} label="Phone" value={creator?.phone || "—"} />
                <Separator />
                <InfoRow icon={Landmark} label="Payout method" value={creator?.payout_method} />
                <InfoRow icon={Receipt} label="Payout account" value={creator?.payout_account || "—"} mono />
                <InfoRow icon={Receipt} label="Tax status" value={<StatusBadge status={creator?.tax_status ?? ""} />} />
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Minimum payout override</span>
                  <span className="tnum font-medium">{creator?.minimum_payout ? formatMoney(creator.minimum_payout) : "Rule default"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Member since</span>
                  <span>{formatDate(creator?.created_at)}</span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardContent className="pt-5">
            <Tabs defaultValue="jobs">
              <TabsList>
                <TabsTrigger value="jobs">Jobs</TabsTrigger>
                <TabsTrigger value="earnings">Earnings</TabsTrigger>
                <TabsTrigger value="payouts">Payouts</TabsTrigger>
              </TabsList>

              <TabsContent value="jobs">
                <CreatorJobs creatorId={id} />
              </TabsContent>
              <TabsContent value="earnings">
                <CreatorEarnings creatorId={id} />
              </TabsContent>
              <TabsContent value="payouts">
                <CreatorPayouts creatorId={id} />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      {creator && (
        <CreatorFormDialog
          open={editOpen} onOpenChange={setEditOpen} mode="edit" creator={creator}
          busy={editMutation.isPending} formError={formError}
          onSubmit={(values) => editMutation.mutate(values)}
        />
      )}
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, mono }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string; value: React.ReactNode; mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" /> {label}
      </span>
      <span className={mono ? "truncate font-mono text-xs" : "truncate font-medium"}>{value}</span>
    </div>
  );
}

function CreatorJobs({ creatorId }: { creatorId: string }) {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["creator-jobs", creatorId],
    queryFn: () => api.get<Paged<Job>>("/jobs/", { creator: creatorId, page_size: 8 }),
  });
  if (isLoading) return <TableSkeleton rows={5} cols={5} />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Job</TableHead><TableHead>Status</TableHead>
          <TableHead className="text-right">Base</TableHead>
          <TableHead>Completed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.results.map((j) => (
          <TableRow key={j.id} className="cursor-pointer" onClick={() => router.push(`/jobs/${j.id}`)}>
            <TableCell className="max-w-[240px] truncate font-medium">{j.title}</TableCell>
            <TableCell><StatusBadge status={j.status} /></TableCell>
            <TableCell className="text-right tnum">{formatMoney(j.base_amount)}</TableCell>
            <TableCell className="text-muted-foreground">{formatDate(j.completed_at)}</TableCell>
          </TableRow>
        ))}
        {data?.results.length === 0 && (
          <TableRow><TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">No jobs yet.</TableCell></TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function CreatorEarnings({ creatorId }: { creatorId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["creator-earnings", creatorId],
    queryFn: () => api.get<Paged<Earning>>("/earnings/", { creator: creatorId, page_size: 8 }),
  });
  if (isLoading) return <TableSkeleton rows={5} cols={5} />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Job</TableHead><TableHead className="text-right">Gross</TableHead>
          <TableHead className="text-right">Fee</TableHead>
          <TableHead className="text-right">Net</TableHead><TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.results.map((e) => (
          <TableRow key={e.id}>
            <TableCell className="max-w-[240px] truncate font-medium">{e.job_title}</TableCell>
            <TableCell className="text-right tnum">{formatMoney(e.gross_amount)}</TableCell>
            <TableCell className="text-right tnum text-muted-foreground">−{formatMoney(e.platform_fee)}</TableCell>
            <TableCell className="text-right tnum font-medium">{formatMoney(e.net_amount)}</TableCell>
            <TableCell><StatusBadge status={e.payout_status} /></TableCell>
          </TableRow>
        ))}
        {data?.results.length === 0 && (
          <TableRow><TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">No earnings yet.</TableCell></TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function CreatorPayouts({ creatorId }: { creatorId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["creator-payouts", creatorId],
    queryFn: () => api.get<Paged<CreatorPayout>>("/payouts/", { creator: creatorId, page_size: 8 }),
  });
  if (isLoading) return <TableSkeleton rows={5} cols={5} />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Period</TableHead><TableHead className="text-right">Net</TableHead>
          <TableHead>Status</TableHead><TableHead>Processed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.results.map((p) => (
          <TableRow key={p.id}>
            <TableCell className="font-medium">{periodLabel(p.period_start, p.period_end)}</TableCell>
            <TableCell className="text-right tnum">{formatMoney(p.net_amount)}</TableCell>
            <TableCell><StatusBadge status={p.status} /></TableCell>
            <TableCell className="text-muted-foreground">{formatDateTime(p.processed_at)}</TableCell>
          </TableRow>
        ))}
        {data?.results.length === 0 && (
          <TableRow><TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">No payouts yet.</TableCell></TableRow>
        )}
      </TableBody>
    </Table>
  );
}

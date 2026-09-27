"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheckBig, MoreHorizontal, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { JobFormDialog, type JobFormValues } from "./job-form";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { ErrorState, NoResultsState, EmptyState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CreatorProfile, Job, Paged } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function JobsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toast } = useToast();
  const { isAdmin } = useAuth();

  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [creator, setCreator] = React.useState("");
  const [ordering, setOrdering] = React.useState("-created_at");

  const [createOpen, setCreateOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<Job | null>(null);
  const [completeTarget, setCompleteTarget] = React.useState<Job | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const { data: creators } = useQuery({
    queryKey: ["creators", "all-simple"],
    queryFn: () => api.get<Paged<CreatorProfile>>("/creators/", { page_size: 100 }),
    enabled: isAdmin,
  });

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["jobs", page, search, status, creator, ordering],
    queryFn: () =>
      api.get<Paged<Job>>("/jobs/", {
        page, page_size: PAGE_SIZE,
        search: search || undefined,
        status: status || undefined,
        creator: creator || undefined,
        ordering,
      }),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["jobs"] });
    qc.invalidateQueries({ queryKey: ["earnings"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const createMutation = useMutation({
    mutationFn: (values: JobFormValues) => api.post<Job>("/jobs/", values),
    onSuccess: () => {
      toast({ title: "Job created", variant: "success" });
      setCreateOpen(false); setFormError(null); invalidate();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Failed to create job."),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: JobFormValues }) =>
      api.patch<Job>(`/jobs/${id}/`, {
        title: values.title, description: values.description,
        base_amount: values.base_amount, surge_multiplier: values.surge_multiplier,
        tip_amount: values.tip_amount,
      }),
    onSuccess: () => {
      toast({ title: "Job updated", variant: "success" });
      setEditTarget(null); setFormError(null); invalidate();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Failed to update job."),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => api.post<Job>(`/jobs/${id}/complete/`, {}),
    onSuccess: () => {
      toast({ title: "Job completed", description: "Earnings calculated with the active payout rule.", variant: "success" });
      setCompleteTarget(null); invalidate();
    },
    onError: (e) =>
      toast({ title: "Could not complete job", description: e instanceof ApiError ? e.message : undefined, variant: "error" }),
  });

  const filtered = search || status || creator;

  return (
    <div>
      <PageHeader title="Jobs" description={isAdmin ? "Marketplace jobs that drive creator earnings." : "Your marketplace jobs."}>
        {isAdmin && (
          <Button onClick={() => { setFormError(null); setCreateOpen(true); }}>
            <Plus /> New job
          </Button>
        )}
      </PageHeader>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search jobs…" />
        <Select value={status || "all"} onValueChange={(v) => { setStatus(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="IN_PROGRESS">In progress</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
          </SelectContent>
        </Select>
        {isAdmin && (
          <Select value={creator || "all"} onValueChange={(v) => { setCreator(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-full sm:w-52"><SelectValue placeholder="Creator" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All creators</SelectItem>
              {creators?.results.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>{c.display_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select value={ordering} onValueChange={setOrdering}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="-created_at">Newest first</SelectItem>
            <SelectItem value="created_at">Oldest first</SelectItem>
            <SelectItem value="-completed_at">Recently completed</SelectItem>
            <SelectItem value="-base_amount">Highest base</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={8} cols={6} />
        ) : (data?.count ?? 0) === 0 ? (
          filtered ? (
            <NoResultsState onReset={() => { setSearch(""); setStatus(""); setCreator(""); }} />
          ) : (
            <EmptyState title="No jobs yet"
                        description={isAdmin ? "Create a job, then complete it to generate earnings." : "Jobs assigned to you will appear here."}
                        action={isAdmin ? <Button size="sm" onClick={() => setCreateOpen(true)}><Plus /> New job</Button> : undefined} />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  {isAdmin && <TableHead>Creator</TableHead>}
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Base</TableHead>
                  <TableHead className="text-right">Surge</TableHead>
                  <TableHead className="text-right">Tips</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((j) => (
                  <TableRow key={j.id} className="cursor-pointer" onClick={() => router.push(`/jobs/${j.id}`)}>
                    <TableCell className="max-w-[240px]">
                      <div className="truncate font-medium">{j.title}</div>
                    </TableCell>
                    {isAdmin && <TableCell className="text-muted-foreground">{j.creator_name}</TableCell>}
                    <TableCell><StatusBadge status={j.status} /></TableCell>
                    <TableCell className="text-right tnum">{formatMoney(j.base_amount)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">×{parseFloat(j.surge_multiplier).toFixed(2)}</TableCell>
                    <TableCell className="text-right tnum text-muted-foreground">{formatMoney(j.tip_amount)}</TableCell>
                    <TableCell className="text-right tnum font-medium">{j.earning_net ? formatMoney(j.earning_net) : "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(j.completed_at)}</TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Row actions">
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => router.push(`/jobs/${j.id}`)}>View details</DropdownMenuItem>
                          {isAdmin && (
                            <>
                              <DropdownMenuItem disabled={j.status === "COMPLETED" || j.status === "CANCELLED"}
                                                onClick={() => { setFormError(null); setEditTarget(j); }}>
                                Edit job
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem disabled={j.status === "COMPLETED" || j.status === "CANCELLED"}
                                                onClick={() => setCompleteTarget(j)}>
                                <CircleCheckBig /> Mark completed
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={data!.page} totalPages={data!.total_pages} count={data!.count}
                        pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      <JobFormDialog open={createOpen} onOpenChange={setCreateOpen} busy={createMutation.isPending}
                     formError={formError} onSubmit={(v) => createMutation.mutate(v)} />
      <JobFormDialog open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)} job={editTarget}
                     busy={editMutation.isPending} formError={formError}
                     onSubmit={(v) => { if (editTarget) editMutation.mutate({ id: editTarget.id, values: v }); }} />
      <ConfirmDialog
        open={!!completeTarget} onOpenChange={(o) => !o && setCompleteTarget(null)}
        title={`Complete “${completeTarget?.title}”?`}
        description="The system will calculate gross earnings, apply surge and tips, deduct the platform fee and create the earning record."
        confirmLabel="Complete job" busy={completeMutation.isPending}
        onConfirm={() => { if (completeTarget) completeMutation.mutate(completeTarget.id); }}
      />
    </div>
  );
}

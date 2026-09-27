"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Plus, UserCheck, UserX } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { CreatorFormDialog, type CreatorFormValues } from "./creator-form";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState, NoResultsState, TableSkeleton } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Pagination } from "@/components/ui/pagination";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { CreatorProfile, Paged } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function CreatorsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toast } = useToast();

  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [method, setMethod] = React.useState("");
  const [tax, setTax] = React.useState("");
  const [ordering, setOrdering] = React.useState("-created_at");

  const [createOpen, setCreateOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<CreatorProfile | null>(null);
  const [suspendTarget, setSuspendTarget] = React.useState<CreatorProfile | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const queryKey = ["creators", page, search, method, tax, ordering];
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey,
    queryFn: () =>
      api.get<Paged<CreatorProfile>>("/creators/", {
        page, page_size: PAGE_SIZE,
        search: search || undefined,
        payout_method: method || undefined,
        tax_status: tax || undefined,
        ordering,
      }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["creators"] });

  const createMutation = useMutation({
    mutationFn: (values: Partial<CreatorFormValues>) =>
      api.post<CreatorProfile>("/creators/", {
        ...values,
        minimum_payout: values.minimum_payout || null,
      }),
    onSuccess: () => {
      toast({ title: "Creator created", variant: "success" });
      setCreateOpen(false);
      setFormError(null);
      invalidate();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Failed to create creator."),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: Partial<CreatorFormValues> }) =>
      api.patch<CreatorProfile>(`/creators/${id}/`, {
        ...values,
        minimum_payout: values.minimum_payout === "" ? null : values.minimum_payout,
      }),
    onSuccess: () => {
      toast({ title: "Creator updated", variant: "success" });
      setEditTarget(null);
      setFormError(null);
      invalidate();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.message : "Failed to update creator."),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.patch(`/creators/${id}/`, { status }),
    onSuccess: (_r, vars) => {
      toast({
        title: vars.status === "SUSPENDED" ? "Creator suspended" : "Creator activated",
        variant: "success",
      });
      setSuspendTarget(null);
      invalidate();
    },
    onError: (e) =>
      toast({ title: "Action failed", description: e instanceof ApiError ? e.message : undefined, variant: "error" }),
  });

  const filtered = search || method || tax;

  return (
    <div>
      <PageHeader title="Creators" description="Manage marketplace creators and their payout profiles.">
        <Button onClick={() => { setFormError(null); setCreateOpen(true); }}>
          <Plus /> New creator
        </Button>
      </PageHeader>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search name, email…" />
        <Select value={method || "all"} onValueChange={(v) => { setMethod(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue placeholder="Payout method" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All methods</SelectItem>
            <SelectItem value="BANK">Bank</SelectItem>
            <SelectItem value="PAYPAL">PayPal</SelectItem>
            <SelectItem value="OTHER">Other</SelectItem>
          </SelectContent>
        </Select>
        <Select value={tax || "all"} onValueChange={(v) => { setTax(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue placeholder="Tax status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tax statuses</SelectItem>
            <SelectItem value="NOT_SUBMITTED">Not submitted</SelectItem>
            <SelectItem value="SUBMITTED">Submitted</SelectItem>
            <SelectItem value="VERIFIED">Verified</SelectItem>
          </SelectContent>
        </Select>
        <Select value={ordering} onValueChange={setOrdering}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="-created_at">Newest first</SelectItem>
            <SelectItem value="created_at">Oldest first</SelectItem>
            <SelectItem value="display_name">Name A→Z</SelectItem>
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
            <NoResultsState onReset={() => { setSearch(""); setMethod(""); setTax(""); }} />
          ) : (
            <EmptyState title="No creators yet"
                        description="Create your first creator to start tracking earnings."
                        action={<Button size="sm" onClick={() => setCreateOpen(true)}><Plus /> New creator</Button>} />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Creator</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Payout</TableHead>
                  <TableHead>Tax</TableHead>
                  <TableHead className="text-right">Min payout</TableHead>
                  <TableHead>Account</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((c) => (
                  <TableRow key={c.id} className="cursor-pointer" onClick={() => router.push(`/creators/${c.id}`)}>
                    <TableCell>
                      <Link href={`/creators/${c.id}`} className="font-medium hover:text-primary" onClick={(e) => e.stopPropagation()}>
                        {c.display_name}
                      </Link>
                      <div className="text-xs text-muted-foreground">{c.email}</div>
                    </TableCell>
                    <TableCell className="text-muted-foreground tnum">{c.phone || "—"}</TableCell>
                    <TableCell><StatusBadge status={c.status} /> <span className="ml-1 text-xs text-muted-foreground">{c.payout_method}</span></TableCell>
                    <TableCell><StatusBadge status={c.tax_status} /></TableCell>
                    <TableCell className="text-right tnum">{c.minimum_payout ? formatMoney(c.minimum_payout) : "—"}</TableCell>
                    <TableCell className="max-w-[160px] truncate text-xs text-muted-foreground">{c.payout_account || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(c.created_at)}</TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Row actions">
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => router.push(`/creators/${c.id}`)}>View details</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => { setFormError(null); setEditTarget(c); }}>Edit profile</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {c.status === "ACTIVE" ? (
                            <DropdownMenuItem className="text-destructive" onClick={() => setSuspendTarget(c)}>
                              <UserX /> Suspend account
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => statusMutation.mutate({ id: c.id, status: "ACTIVE" })}>
                              <UserCheck /> Reactivate account
                            </DropdownMenuItem>
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

      <CreatorFormDialog
        open={createOpen} onOpenChange={setCreateOpen} mode="create"
        busy={createMutation.isPending} formError={formError}
        onSubmit={(values) => createMutation.mutate(values)}
      />
      <CreatorFormDialog
        open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)} mode="edit"
        creator={editTarget} busy={editMutation.isPending} formError={formError}
        onSubmit={(values) => { if (editTarget) editMutation.mutate({ id: editTarget.id, values }); }}
      />
      <ConfirmDialog
        open={!!suspendTarget} onOpenChange={(o) => !o && setSuspendTarget(null)}
        title={`Suspend ${suspendTarget?.display_name}?`}
        description="Suspended creators cannot log in. Their earnings and history are preserved."
        confirmLabel="Suspend" destructive busy={statusMutation.isPending}
        onConfirm={() => { if (suspendTarget) statusMutation.mutate({ id: suspendTarget.id, status: "SUSPENDED" }); }}
      />
    </div>
  );
}

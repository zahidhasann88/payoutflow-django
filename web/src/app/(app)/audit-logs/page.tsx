"use client";

import { useQuery } from "@tanstack/react-query";
import { Braces, ScrollText } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState, NoResultsState, TableSkeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { AuditLog, Paged } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 25;

const ACTIONS = [
  "LOGIN", "CREATOR_CREATED", "CREATOR_UPDATED", "JOB_CREATED", "JOB_UPDATED",
  "JOB_COMPLETED", "PAYOUT_RULE_CHANGED", "PAYOUT_BATCH_CREATED",
  "PAYOUT_BATCH_PROCESSED", "PAYOUT_FAILED", "ADJUSTMENT_CREATED", "USER_UPDATED",
];

export default function AuditLogsPage() {
  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [action, setAction] = React.useState("");
  const [detail, setDetail] = React.useState<AuditLog | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["audit-logs", page, search, action],
    queryFn: () =>
      api.get<Paged<AuditLog>>("/audit-logs/", {
        page, page_size: PAGE_SIZE,
        search: search || undefined,
        action: action || undefined,
      }),
  });

  const filtered = search || action;

  return (
    <div>
      <PageHeader title="Audit logs"
                  description="Append-only trail of important actions. Secrets, passwords and tokens are never logged." />

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Search user, entity…" />
        <Select value={action || "all"} onValueChange={(v) => { setAction(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-64"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {ACTIONS.map((a) => (
              <SelectItem key={a} value={a}>{a.replaceAll("_", " ").toLowerCase()}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-card">
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={10} cols={5} />
        ) : (data?.count ?? 0) === 0 ? (
          filtered ? (
            <NoResultsState onReset={() => { setSearch(""); setAction(""); }} />
          ) : (
            <EmptyState icon={ScrollText} title="No audit events yet" />
          )
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead className="w-20" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.results.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                    <TableCell>
                      <div className="font-medium">{log.user_name ?? "System"}</div>
                      <div className="text-xs text-muted-foreground">{log.user_email ?? ""}</div>
                    </TableCell>
                    <TableCell><Badge variant="secondary">{log.action.replaceAll("_", " ").toLowerCase()}</Badge></TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.entity_type ? `${log.entity_type} · ${log.entity_id.slice(0, 12)}` : "—"}
                    </TableCell>
                    <TableCell>
                      {log.metadata && Object.keys(log.metadata).length > 0 && (
                        <Button variant="ghost" size="sm" onClick={() => setDetail(log)}>
                          <Braces className="h-3.5 w-3.5" /> Data
                        </Button>
                      )}
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

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{detail?.action.replaceAll("_", " ").toLowerCase()}</DialogTitle>
          </DialogHeader>
          <pre className="max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs leading-relaxed">
            {detail ? JSON.stringify(detail.metadata, null, 2) : ""}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}

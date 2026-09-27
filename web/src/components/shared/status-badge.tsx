import { Badge } from "@/components/ui/badge";

const MAP: Record<string, { label: string; variant: "default" | "secondary" | "success" | "warning" | "destructive" | "info" | "muted" }> = {
  ACTIVE: { label: "Active", variant: "success" },
  SUSPENDED: { label: "Suspended", variant: "destructive" },
  PENDING: { label: "Pending", variant: "warning" },
  IN_PROGRESS: { label: "In progress", variant: "info" },
  COMPLETED: { label: "Completed", variant: "success" },
  CANCELLED: { label: "Cancelled", variant: "muted" },
  INCLUDED: { label: "In batch", variant: "info" },
  PAID: { label: "Paid", variant: "success" },
  DRAFT: { label: "Draft", variant: "muted" },
  READY: { label: "Ready", variant: "info" },
  PROCESSING: { label: "Processing", variant: "warning" },
  FAILED: { label: "Failed", variant: "destructive" },
  NOT_SUBMITTED: { label: "Not submitted", variant: "muted" },
  SUBMITTED: { label: "Submitted", variant: "info" },
  VERIFIED: { label: "Verified", variant: "success" },
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const entry = MAP[status] ?? { label: status, variant: "secondary" as const };
  return <Badge variant={entry.variant} className={className}>{entry.label}</Badge>;
}

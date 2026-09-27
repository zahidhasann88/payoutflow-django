export type Role = "ADMIN" | "CREATOR";
export type UserStatus = "ACTIVE" | "SUSPENDED";
export type PayoutMethod = "BANK" | "PAYPAL" | "OTHER";
export type TaxStatus = "NOT_SUBMITTED" | "SUBMITTED" | "VERIFIED";
export type JobStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type EarningPayoutStatus = "PENDING" | "INCLUDED" | "PAID";
export type BatchStatus = "DRAFT" | "READY" | "PROCESSING" | "COMPLETED" | "FAILED";
export type PayoutStatus = "PENDING" | "PROCESSING" | "PAID" | "FAILED";

export interface CreatorProfile {
  id: number;
  user: string;
  email: string;
  name: string;
  status: UserStatus;
  role: Role;
  display_name: string;
  phone: string;
  payout_method: PayoutMethod;
  payout_account: string;
  tax_status: TaxStatus;
  minimum_payout: string | null;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: UserStatus;
  created_at: string;
  updated_at: string;
  creator: CreatorProfile | null;
}

export interface Job {
  id: number;
  creator: number;
  creator_name: string;
  title: string;
  description: string;
  status: JobStatus;
  base_amount: string;
  surge_multiplier: string;
  tip_amount: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  earning_net: string | null;
}

export interface Adjustment {
  id: number;
  earning: number;
  amount: string;
  reason: string;
  created_by: string | null;
  created_by_email: string | null;
  created_at: string;
}

export interface Earning {
  id: number;
  job: number;
  job_id: number;
  job_title: string;
  creator: number;
  creator_name: string;
  base_amount: string;
  surge_amount: string;
  tip_amount: string;
  gross_amount: string;
  platform_fee: string;
  fee_percentage_applied: string;
  adjustment_amount: string;
  net_amount: string;
  payout_status: EarningPayoutStatus;
  payout_id: number | null;
  adjustments: Adjustment[];
  created_at: string;
  updated_at: string;
}

export interface PayoutRule {
  id: number;
  name: string;
  platform_fee_percentage: string;
  minimum_payout: string;
  payout_frequency: "WEEKLY";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatorPayout {
  id: number;
  payout_batch: number;
  creator: number;
  creator_name: string;
  period_start: string;
  period_end: string;
  batch_status: BatchStatus;
  gross_amount: string;
  platform_fee: string;
  adjustments: string;
  net_amount: string;
  earning_count: number;
  status: PayoutStatus;
  processed_at: string | null;
  failure_reason: string;
  created_at: string;
  updated_at: string;
}

export interface PayoutBatch {
  id: number;
  period_start: string;
  period_end: string;
  creator_count: number;
  gross_amount: string;
  platform_fee: string;
  net_amount: string;
  payout_rule_snapshot: Record<string, string>;
  status: BatchStatus;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  payout_count?: number;
  paid_count?: number;
  failed_count?: number;
  rule_name?: string | null;
  fee_percentage?: string | null;
  payouts?: CreatorPayout[];
}

export interface AuditLog {
  id: number;
  user: string | null;
  user_email: string | null;
  user_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Paged<T> {
  success: boolean;
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: T[];
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
}

export interface AdminDashboard {
  cards: {
    total_creators: number;
    month_gross: string;
    month_platform_fees: string;
    total_paid: string;
    total_paid_count: number;
    pending_payout_amount: string;
    pending_payout_count: number;
    pending_earnings_amount: string;
    pending_earnings_count: number;
  };
  chart: {
    weekly: { period: string; gross: string; fees: string; net: string }[];
    monthly: { period: string; gross: string; fees: string; net: string }[];
  };
  recent_batches: PayoutBatch[];
  recent_activity: AuditLog[];
  payout_cron: string;
}

export interface CreatorDashboard {
  cards: {
    current_earnings: string;
    current_earnings_count: number;
    pending_payout: string;
    pending_payout_count: number;
    paid_this_month: string;
    total_earnings: string;
    total_gross: string;
  };
  recent_jobs: Job[];
  recent_payouts: CreatorPayout[];
}

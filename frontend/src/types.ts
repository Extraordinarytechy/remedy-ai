export interface ReceiptData {
  store_name?: string | null;
  purchase_date?: string | null;
  item_description?: string | null;
  total_amount?: number | null;
  currency?: string | null;
  currency_evidence?: string | null;
  payment_type?: string | null;
  confidence_score?: number | null;
  source: 'textract' | 'sample' | 'unavailable';
}

export interface VisualDefectEvidence {
  anomaly_detected: boolean;
  visible_physical_damage: boolean;
  physical_damage_severity: 'none' | 'cosmetic' | 'screen_cracked' | 'severe';
  symptom_category?: string | null;
  visual_observations: string[];
  source: 'bedrock' | 'sample' | 'unavailable';
}

export interface NormalizedCase {
  case_id: string;
  product_name: string;
  product_brand?: string | null;
  product_model?: string | null;
  purchase_date: string;
  failure_date: string;
  purchase_country: string;
  uk_region?: UkRegion | null;
  retailer?: string | null;
  payment_method?: string | null;
  original_warranty_years: number;
  defect_description: string;
  evaluation_date?: string | null;
  already_paid_for_repair?: boolean;
  confirmed_checks?: string[];
  receipt_data?: ReceiptData | null;
  visual_evidence?: VisualDefectEvidence | null;
}

export type UkRegion = 'england_wales' | 'northern_ireland' | 'scotland';

export type RouteStatus =
  | 'POTENTIALLY_ELIGIBLE'
  | 'ELIGIBLE_PENDING_INSPECTION'
  | 'PENDING_SERIAL_VERIFICATION'
  | 'NEEDS_REVERIFICATION'
  | 'NEEDS_CONFIRMATION'
  | 'OUTSIDE_WINDOW'
  | 'INSUFFICIENT_EVIDENCE';

export interface CaseCheck {
  id: string;
  severity: 'hard' | 'soft';
  message: string;
  confirm_label?: string | null;
  confirmed: boolean;
}

export interface CaseTimeline {
  purchase_date: string;
  failure_date: string;
  claim_date: string;
  months_before_failure: number;
}

export interface SourceCheck {
  checked_at?: string;
  http_status?: number;
  reachable?: boolean;
  last_changed_at?: string;
  human_verified_at?: string;
  listed_on_apple_index?: boolean | null;
}

export interface MatchedRoute {
  route_id: string;
  route_type: 'manufacturer_warranty' | 'manufacturer_service_program' | 'card_benefit' | 'statutory_consumer_law';
  title: string;
  provider: string;
  status: RouteStatus;
  summary: string;
  primary_source: { title: string; url: string; verified_at: string };
  provenance: {
    claim: string;
    why_matched: string;
    evidence: string[];
    source_citation: string;
    source_url: string;
    conditions: string[];
    exceptions: string[];
  };
  recommended_action: string;
  deadline?: string | null;
  deadline_label?: string | null;
  days_left?: number | null;
  related_sources?: { title: string; url: string }[];
  source_check?: SourceCheck | null;
}

export interface RemedyEvaluation {
  case_id: string;
  evaluated_at: string;
  evaluation_date?: string | null;
  has_coverage: boolean;
  matched_routes: MatchedRoute[];
  unmatched_reason?: string | null;
  notes: string[];
  next_steps: string[];
  timeline?: CaseTimeline | null;
  checks: CaseCheck[];
  pdf_allowed: boolean;
  disclaimer: string;
}

export interface SourceEntry {
  id: string;
  program_name: string;
  issuer: string;
  source_url: string;
  human_verified_at: string;
  watch: SourceCheck & { first_seen_at?: string; changed_this_run?: boolean };
}

export interface SourcesResponse {
  sources: SourceEntry[];
  apple_index?: {
    url: string;
    checked_at: string;
    http_status: number;
    titles: string[];
    added_since_last_check: string[];
    removed_since_last_check: string[];
    uncovered_service_programs?: string[];
    uncovered_recall_or_exchange_programs?: string[];
  } | null;
}

export interface ExtractResponse {
  receipt_data: ReceiptData | null;
  visual_evidence: VisualDefectEvidence | null;
}

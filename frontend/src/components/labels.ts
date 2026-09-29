import type { RouteStatus } from '../types';

export const STATUS_LABEL: Record<RouteStatus, { text: string; tone: string }> = {
  ELIGIBLE_PENDING_INSPECTION: { text: 'Likely covered, pending inspection', tone: 'emerald' },
  PENDING_SERIAL_VERIFICATION: { text: 'Possible: check your serial number', tone: 'sky' },
  POTENTIALLY_ELIGIBLE: { text: 'Possible route', tone: 'sky' },
  NEEDS_REVERIFICATION: { text: 'Source changed: re-verify first', tone: 'amber' },
  OUTSIDE_WINDOW: { text: 'Outside the window', tone: 'rose' },
  INSUFFICIENT_EVIDENCE: { text: 'Not enough evidence', tone: 'rose' },
};

export const TONE_CLASSES: Record<string, string> = {
  emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  sky: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  slate: 'bg-slate-700/60 text-slate-200 border-slate-600',
};

export const ROUTE_TYPE_LABEL = {
  manufacturer_service_program: 'Manufacturer service program',
  card_benefit: 'Payment-card benefit',
  statutory_consumer_law: 'Consumer law',
} as const;

export function formatMoney(amount?: number | null, currency?: string | null): string {
  if (amount == null) return 'Not recorded';
  try {
    return new Intl.NumberFormat('en', { style: 'currency', currency: currency || 'USD' }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency ?? ''}`.trim();
  }
}

export function shortDate(iso?: string | null): string {
  return iso ? iso.slice(0, 10) : 'never';
}

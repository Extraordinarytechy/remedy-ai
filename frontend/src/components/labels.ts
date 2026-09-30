import type { MatchedRoute, RouteStatus, UkRegion } from '../types';

export const STATUS_LABEL: Record<RouteStatus, { text: string; tone: string }> = {
  ELIGIBLE_PENDING_INSPECTION: { text: 'Likely, after an inspection', tone: 'emerald' },
  PENDING_SERIAL_VERIFICATION: { text: 'Possible: check your serial number', tone: 'sky' },
  POTENTIALLY_ELIGIBLE: { text: 'May apply', tone: 'sky' },
  NEEDS_REVERIFICATION: { text: 'Source changed: check it first', tone: 'amber' },
  NEEDS_CONFIRMATION: { text: 'Confirm your details first', tone: 'amber' },
  OUTSIDE_WINDOW: { text: 'Window closed', tone: 'rose' },
  INSUFFICIENT_EVIDENCE: { text: 'Not enough evidence', tone: 'rose' },
};

export const TONE_CLASSES: Record<string, string> = {
  emerald: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/40',
  sky: 'bg-sky-500/15 text-sky-200 border-sky-400/40',
  amber: 'bg-amber-500/15 text-amber-200 border-amber-400/40',
  rose: 'bg-rose-500/15 text-rose-200 border-rose-400/40',
  slate: 'bg-slate-700/60 text-slate-100 border-slate-500',
};

export const ROUTE_TYPE_LABEL = {
  manufacturer_warranty: "The maker's own warranty",
  manufacturer_service_program: 'Free repair program from the maker',
  card_benefit: 'Benefit from the card you paid with',
  statutory_consumer_law: 'Your rights under consumer law',
} as const;

export const UK_REGIONS: { value: UkRegion; label: string }[] = [
  { value: 'england_wales', label: 'England or Wales' },
  { value: 'northern_ireland', label: 'Northern Ireland' },
  { value: 'scotland', label: 'Scotland' },
];

/** One plain sentence for the top of the result, per option. */
export function verdictFor(route: MatchedRoute): string {
  if (route.status === 'NEEDS_CONFIRMATION') return 'Confirm where you bought it before relying on this option.';
  if (route.status === 'NEEDS_REVERIFICATION') return `The source for "${route.title}" has changed. Check it before you rely on it.`;
  switch (route.route_type) {
    case 'manufacturer_warranty':
      return `${route.provider.replace(' Inc.', '')}'s warranty may still cover this. Contact ${route.provider.replace(' Inc.', '')} before it ends.`;
    case 'manufacturer_service_program':
      return route.status === 'PENDING_SERIAL_VERIFICATION'
        ? `You may get a free repair from ${route.provider.replace(' Inc.', '')}. First, check your serial number.`
        : `You may get a free repair from ${route.provider.replace(' Inc.', '')}.`;
    case 'card_benefit':
      return 'The card you paid with may add a year to the warranty. Ask your card issuer.';
    case 'statutory_consumer_law':
      return 'The store that sold it may owe you a repair or replacement.';
  }
}

export function formatMoney(amount?: number | null, currency?: string | null): string {
  if (amount == null) return 'Not recorded';
  try {
    return new Intl.NumberFormat('en', { style: 'currency', currency: currency || 'USD' }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency ?? ''}`.trim();
  }
}

/** "2023-11-24" -> "24 Nov 2023". Parsed as a calendar date, so no time-zone shift. */
export function humanDate(iso?: string | null): string {
  if (!iso) return 'Not given';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]}`;
}

export function shortDate(iso?: string | null): string {
  return iso ? humanDate(iso.slice(0, 10)) : 'never';
}

export function daysLeftText(days?: number | null): string {
  if (days == null) return '';
  if (days < 0) return 'ended';
  if (days === 0) return 'ends today';
  if (days < 60) return `${days} days left`;
  const months = Math.floor(days / 30.4);
  return months < 24 ? `about ${months} months left` : `about ${Math.floor(months / 12)} years left`;
}

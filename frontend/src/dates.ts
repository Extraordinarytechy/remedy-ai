/*
 * Date helpers that work on calendar dates (YYYY-MM-DD strings), never on time-zone-shifted
 * Date objects, so a date typed in one time zone can't turn into the day before.
 */

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/**
 * Purchases more than this many years before today are refused. Mirrors MAX_PURCHASE_AGE_YEARS
 * in backend/src/engine/eligibility.py, which stays the authority.
 */
export const EARLIEST_PURCHASE_YEARS = 30;

/** Today minus EARLIEST_PURCHASE_YEARS, as YYYY-MM-DD. 29 Feb becomes 28 Feb in a non-leap year. */
export function earliestIso(): string {
  const [y, m, d] = todayIso().split('-').map(Number);
  const year = y - EARLIEST_PURCHASE_YEARS;
  const days = new Date(Date.UTC(year, m, 0)).getUTCDate();
  return `${year}-${String(m).padStart(2, '0')}-${String(Math.min(d, days)).padStart(2, '0')}`;
}

function valid(y: number, m: number, d: number): string | null {
  // Old years are still read, so "1/1/1900" is reported as too long ago rather than unreadable.
  if (y < 1000 || y > 2100 || m < 1 || m > 12 || d < 1) return null;
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
  if (d > days) return null;
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function year(y: string): number {
  const n = Number(y);
  return y.length === 2 ? 2000 + n : n;
}

/**
 * Parses what people actually type: 2023-11-24, 24/11/2023, 11/24/2023, 24.11.23,
 * 24 Nov 2023, Nov 24 2023, November 24, 2023. For ambiguous numeric dates, US uses
 * month/day and everywhere else day/month. Returns YYYY-MM-DD or null.
 */
export function parseTypedDate(input: string, country: string): string | null {
  const s = input.trim().toLowerCase().replace(/,/g, ' ').replace(/\s+/g, ' ');
  if (!s) return null;

  let m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(s);
  if (m) return valid(Number(m[1]), Number(m[2]), Number(m[3]));

  m = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$/.exec(s);
  if (m) {
    const a = Number(m[1]);
    const b = Number(m[2]);
    const y = year(m[3]);
    // If only one reading is possible, use it; otherwise follow the country's convention.
    if (a > 12) return valid(y, b, a);
    if (b > 12) return valid(y, a, b);
    return country === 'US' ? valid(y, a, b) : valid(y, b, a);
  }

  const month = (w: string) => MONTHS.findIndex((mm) => w.startsWith(mm)) + 1;
  m = /^(\d{1,2})(?:st|nd|rd|th)? ([a-z]+)\.? (\d{2}|\d{4})$/.exec(s);
  if (m && month(m[2])) return valid(year(m[3]), month(m[2]), Number(m[1]));
  m = /^([a-z]+)\.? (\d{1,2})(?:st|nd|rd|th)? (\d{2}|\d{4})$/.exec(s);
  if (m && month(m[1])) return valid(year(m[3]), month(m[1]), Number(m[2]));

  return null;
}

export function formatIso(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1][0].toUpperCase()}${MONTHS[Number(m[2]) - 1].slice(1)} ${m[1]}`;
}

/** Example format shown to the user, matching how parseTypedDate reads numeric dates. */
export function exampleFormat(country: string): string {
  return country === 'US' ? 'MM/DD/YYYY' : 'DD/MM/YYYY';
}

/*
 * Calendar file (.ics) for a deadline. Built in the browser; nothing is sent or stored.
 * One all-day event on the deadline, with reminders 14 days and 1 day before.
 */
function icsEscape(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

function foldLine(line: string): string {
  const out: string[] = [];
  let rest = line;
  while (rest.length > 74) {
    out.push(rest.slice(0, 74));
    rest = ' ' + rest.slice(74);
  }
  out.push(rest);
  return out.join('\r\n');
}

export function deadlineIcs(opts: { deadline: string; title: string; description: string; url?: string; uid: string }): string {
  const day = opts.deadline.replace(/-/g, '');
  const next = (() => {
    const [y, mo, d] = opts.deadline.split('-').map(Number);
    const t = new Date(Date.UTC(y, mo - 1, d + 1));
    return `${t.getUTCFullYear()}${String(t.getUTCMonth() + 1).padStart(2, '0')}${String(t.getUTCDate()).padStart(2, '0')}`;
  })();
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//RemedyAI//Deadline reminder//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${opts.uid}@remedyai`,
    `DTSTAMP:${stamp}`,
    `DTSTART;VALUE=DATE:${day}`,
    `DTEND;VALUE=DATE:${next}`,
    `SUMMARY:${icsEscape(opts.title)}`,
    `DESCRIPTION:${icsEscape(opts.description)}`,
    ...(opts.url ? [`URL:${opts.url}`] : []),
    'TRANSP:TRANSPARENT',
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    `DESCRIPTION:${icsEscape(opts.title)}`,
    'TRIGGER:-P14D',
    'END:VALARM',
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    `DESCRIPTION:${icsEscape(opts.title)}`,
    'TRIGGER:-P1D',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];
  return lines.map(foldLine).join('\r\n') + '\r\n';
}

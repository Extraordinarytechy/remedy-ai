import { useState } from 'react';
import { AlertTriangle, ArrowUpRight, CalendarClock, CalendarPlus, Check, ClipboardList, Copy, Download, FileSearch, RefreshCw } from 'lucide-react';
import type { MatchedRoute, NormalizedCase } from '../types';
import { deadlineIcs } from '../dates';
import { ROUTE_TYPE_LABEL, STATUS_LABEL, TONE_CLASSES, daysLeftText, humanDate, isActionable, shortDate } from './labels';
import { Disclosure } from './ui';

interface Props {
  route: MatchedRoute;
  index: number;
  c: NormalizedCase;
  onDownload: () => void;
  downloading: boolean;
  pdfAllowed: boolean;
}

export function RouteCard({ route, index, c, onDownload, downloading, pdfAllowed }: Props) {
  const [copied, setCopied] = useState(false);
  const status = STATUS_LABEL[route.status];
  const check = route.source_check;
  const serialCheck = route.status === 'PENDING_SERIAL_VERIFICATION';
  const actionable = isActionable(route);

  // Builds a calendar file in the browser: an all-day event on the deadline with reminders
  // 14 days and 1 day before. Nothing is sent or stored.
  const addToCalendar = () => {
    if (!route.deadline) return;
    const ics = deadlineIcs({
      deadline: route.deadline,
      title: `Deadline: ${route.deadline_label ?? 'claim'} (${c.product_name})`,
      description:
        `${route.title}\n${route.deadline_label}: ${humanDate(route.deadline)}.\n\nWhat to do: ${route.recommended_action}\n\n` +
        (route.route_type === 'card_benefit'
          ? "Check now: your issuer's Guide to Benefits sets a deadline to report a claim, usually counted from when the item failed. It can be much earlier than this date.\n\n"
          : '') +
        `Official source: ${route.primary_source.url}\nPrepared with RemedyAI. Not legal advice.`,
      url: route.primary_source.url,
      uid: `${route.route_id}-${route.deadline}-${c.case_id}`,
    });
    const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `RemedyAI_deadline_${route.deadline}.ics`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Same wording as the claim PDF's letter (backend/src/services/pdf_service.py).
  const copyLetter = async () => {
    const cra = 'Under the Consumer Rights Act 2015, goods must be of satisfactory quality, fit for purpose and as described (sections 9 to 11). ';
    const basis =
      route.route_type !== 'statutory_consumer_law'
        ? `Based on the published terms of ${route.title} (${route.primary_source.url}), I believe it may qualify for a remedy, subject to your inspection. `
        : route.short_term_reject
          ? cra +
            'The goods are faulty and I am still within 30 days of delivery (section 22), so I am rejecting them under my short-term right to reject ' +
            'and ask for a full refund (section 20). The refund is due within 14 days of you agreeing that I am entitled to it (section 20(15)). '
          : cra + 'I believe this fault was present when the goods were delivered, so I am asking you to repair or replace them at no cost to me (section 23). ';
    const letter =
      `To: ${route.claim_to ?? route.provider}\nSubject: Claim for ${c.product_name}\n\n` +
      `I bought my ${c.product_name} on ${humanDate(c.purchase_date)}. On ${humanDate(c.failure_date)} it developed this fault: "${c.defect_description}".\n\n` +
      basis +
      `I can provide proof of purchase, photos of the fault and proof of payment.\n\nPlease confirm you have received this and ` +
      (route.short_term_reject ? 'tell me how to return the goods.' : 'tell me the next step.');
    try {
      await navigator.clipboard.writeText(letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      /* clipboard blocked; nothing to do */
    }
  };

  return (
    <article className="card space-y-5 p-6" aria-labelledby={`route-${route.route_id}`}>
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-faint">Option {index}</span>
          <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_CLASSES[status.tone]}`}>{status.text}</span>
        </div>
        <h3 id={`route-${route.route_id}`} className="text-xl font-semibold tracking-tight">{route.title}</h3>
        <p className="text-sm text-muted">{ROUTE_TYPE_LABEL[route.route_type]} · {route.provider}</p>
      </header>

      <section className="space-y-4 rounded-2xl bg-accent-soft p-5">
        <h4 className="flex items-center gap-2 font-semibold text-accent-text">
          <ClipboardList className="size-5" aria-hidden="true" /> What to do next
        </h4>
        {/* The official page is one click away on the button below, so long URLs are left out of the sentence. */}
        <p className="text-[15px] leading-relaxed text-ink">{route.recommended_action.replace(/\s*\(https?:\/\/[^)\s]+\)/g, '')}</p>
        <div className="flex flex-wrap gap-2.5">
          <a href={route.primary_source.url} target="_blank" rel="noopener noreferrer" className="btn-primary">
            {serialCheck ? 'Check your serial number' : 'Open the official page'} <ArrowUpRight className="size-4" aria-hidden="true" />
          </a>
          <button onClick={onDownload} disabled={downloading || !pdfAllowed} className="btn-secondary">
            <Download className="size-4" aria-hidden="true" /> {downloading ? 'Preparing PDF...' : 'Claim PDF'}
          </button>
          {actionable && (
            <button onClick={copyLetter} className="btn-ghost">
              {copied ? <Check className="size-4" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
              {copied ? 'Copied' : 'Copy draft letter'}
            </button>
          )}
          <span role="status" className="sr-only">{copied ? 'Draft letter copied' : ''}</span>
        </div>
        {!actionable ? (
          <p className="text-sm font-medium text-warn-ink">
            Check the official page first. Until then, this option isn't used in the claim letter.
          </p>
        ) : (
          !pdfAllowed && <p className="text-sm font-medium text-warn-ink">Confirm the highlighted details above to get the claim PDF.</p>
        )}
      </section>

      {route.deadline && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-line px-4 py-3">
          <CalendarClock className="size-5 shrink-0 text-accent-text" aria-hidden="true" />
          <p className="text-[15px]">
            <span className="font-semibold">{route.deadline_label}:</span> {humanDate(route.deadline)}
            {route.days_left != null && <span className="text-faint"> · {daysLeftText(route.days_left)}</span>}
          </p>
          {actionable && (route.days_left ?? 0) >= 0 && (
            <button onClick={addToCalendar} className="btn-ghost ml-auto min-h-9 text-sm">
              <CalendarPlus className="size-4" aria-hidden="true" /> Add to calendar
            </button>
          )}
        </div>
      )}

      <div className="space-y-2.5">
        <Disclosure title={<><Check className="size-4 text-accent-text" aria-hidden="true" /> What you'll need</>} meta={`${route.provenance.conditions.length}`}>
          <ul className="list-disc space-y-1.5 pl-5 text-ink">
            {route.provenance.conditions.map((x, i) => <li key={i}>{x}</li>)}
          </ul>
        </Disclosure>
        <Disclosure title={<><AlertTriangle className="size-4 text-warn-ink" aria-hidden="true" /> What could stop it</>} meta={`${route.provenance.exceptions.length}`}>
          <ul className="space-y-2">
            {route.provenance.exceptions.map((x, i) => (
              <li key={i} className="rounded-xl bg-warn-soft px-3 py-2 text-warn-ink">{x}</li>
            ))}
          </ul>
        </Disclosure>
        <Disclosure title={<><FileSearch className="size-4 text-accent-text" aria-hidden="true" /> Why it matched, and sources</>}>
          <div className="space-y-4">
            <div>
              <h5 className="font-semibold text-ink">What this may give you</h5>
              <p className="mt-1 leading-relaxed">{route.provenance.claim}</p>
            </div>
            <div>
              <h5 className="font-semibold text-ink">Why it matched</h5>
              <p className="mt-1 leading-relaxed">{route.provenance.why_matched}</p>
            </div>
            <div>
              <h5 className="font-semibold text-ink">Evidence used</h5>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {route.provenance.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
              </ul>
            </div>
            <div>
              <h5 className="font-semibold text-ink">About this option</h5>
              <p className="mt-1 leading-relaxed">{route.summary}</p>
            </div>
            <div className="space-y-1.5">
              <h5 className="font-semibold text-ink">Sources</h5>
              <a href={route.primary_source.url} target="_blank" rel="noopener noreferrer" className="link inline-flex items-start gap-1">
                {route.primary_source.title} <ArrowUpRight className="mt-1 size-3.5 shrink-0" aria-hidden="true" />
              </a>
              {(route.related_sources ?? []).map((s) => (
                <div key={s.url}>
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="link inline-flex items-start gap-1">
                    {s.title} <ArrowUpRight className="mt-1 size-3.5 shrink-0" aria-hidden="true" />
                  </a>
                </div>
              ))}
              <p className="text-sm">Verified against the official page: {shortDate(route.primary_source.verified_at)}</p>
              <p className="flex items-start gap-1.5 text-sm">
                <RefreshCw className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                {check
                  ? `Checked automatically ${shortDate(check.checked_at)}: page ${check.reachable ? 'online' : `offline (HTTP ${check.http_status})`}` +
                    (check.listed_on_apple_index != null ? `, ${check.listed_on_apple_index ? 'still listed' : 'not listed'} on Apple's program list` : '')
                  : 'No recent automatic check is available for this source.'}
              </p>
            </div>
          </div>
        </Disclosure>
      </div>
    </article>
  );
}

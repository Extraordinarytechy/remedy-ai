import { useState } from 'react';
import { AlertTriangle, CalendarClock, Check, ClipboardList, Copy, Download, ExternalLink, RefreshCw } from 'lucide-react';
import type { MatchedRoute, NormalizedCase } from '../types';
import { ROUTE_TYPE_LABEL, STATUS_LABEL, TONE_CLASSES, daysLeftText, humanDate, shortDate } from './labels';

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

  const copyLetter = async () => {
    const letter =
      `To: ${route.provider}\nSubject: Claim for ${c.product_name}\n\n` +
      `I bought my ${c.product_name} on ${humanDate(c.purchase_date)}. On ${humanDate(c.failure_date)} it developed this fault: "${c.defect_description}".\n\n` +
      `Based on the published terms of ${route.title} (${route.primary_source.url}), I believe it may qualify for a remedy, subject to your inspection. ` +
      `I can provide proof of purchase, photos of the fault and proof of payment.\n\nPlease confirm you have received this and tell me the next step.`;
    await navigator.clipboard.writeText(letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <article className="bg-slate-900/80 border border-slate-700 rounded-2xl p-5 sm:p-6 space-y-5" aria-labelledby={`route-${route.route_id}`}>
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-slate-300">Option {index}</span>
          <span className={`text-sm font-semibold px-2.5 py-0.5 rounded-full border ${TONE_CLASSES[status.tone]}`}>{status.text}</span>
        </div>
        <h3 id={`route-${route.route_id}`} className="text-xl font-bold text-white">{route.title}</h3>
        <p className="text-sm text-slate-300">{ROUTE_TYPE_LABEL[route.route_type]} · {route.provider}</p>
      </header>

      <section className="rounded-xl bg-sky-500/10 border border-sky-400/30 p-4 space-y-3">
        <h4 className="font-semibold text-sky-100 flex items-center gap-2">
          <ClipboardList className="w-5 h-5" aria-hidden="true" /> What to do next
        </h4>
        <p className="text-[15px] text-slate-100 leading-relaxed">{route.recommended_action}</p>
        <div className="flex flex-wrap gap-3">
          <a
            href={route.primary_source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 min-h-11 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-[15px]"
          >
            {serialCheck ? 'Check your serial number' : 'Open the official page'} <ExternalLink className="w-4 h-4" aria-hidden="true" />
          </a>
          <button
            onClick={onDownload}
            disabled={downloading || !pdfAllowed}
            className="inline-flex items-center gap-2 min-h-11 px-4 rounded-lg border border-slate-500 text-slate-50 hover:bg-slate-800 font-medium text-[15px] disabled:opacity-40"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            {downloading ? 'Preparing PDF...' : 'Download claim PDF'}
          </button>
          <button onClick={copyLetter} className="inline-flex items-center gap-2 min-h-11 px-4 rounded-lg text-sky-200 hover:bg-slate-800 font-medium text-[15px]">
            {copied ? <Check className="w-4 h-4" aria-hidden="true" /> : <Copy className="w-4 h-4" aria-hidden="true" />}
            {copied ? 'Copied' : 'Copy a draft letter'}
          </button>
        </div>
        {!pdfAllowed && <p className="text-sm text-amber-200">Confirm the details highlighted above to download the claim PDF.</p>}
      </section>

      {route.deadline && (
        <section className="flex items-start gap-3">
          <CalendarClock className="w-5 h-5 text-slate-300 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-[15px] text-slate-100">
            <span className="font-semibold">{route.deadline_label}:</span> {humanDate(route.deadline)}
            {route.days_left != null && <span className="text-slate-300"> ({daysLeftText(route.days_left)})</span>}
          </p>
        </section>
      )}

      <section>
        <h4 className="font-semibold text-slate-100 mb-2">What you'll need</h4>
        <ul className="list-disc pl-5 space-y-1.5 text-[15px] text-slate-200">
          {route.provenance.conditions.map((cond, i) => <li key={i}>{cond}</li>)}
        </ul>
      </section>

      <section>
        <h4 className="font-semibold text-amber-200 mb-2 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" aria-hidden="true" /> What could stop it
        </h4>
        <ul className="space-y-2">
          {route.provenance.exceptions.map((exc, i) => (
            <li key={i} className="text-[15px] text-amber-50/90 bg-amber-500/5 p-3 rounded-lg border border-amber-400/20">{exc}</li>
          ))}
        </ul>
      </section>

      <details className="group rounded-xl border border-slate-700 bg-slate-950/60">
        <summary className="cursor-pointer min-h-11 flex items-center px-4 font-medium text-slate-100 hover:bg-slate-800/60 rounded-xl">
          See details and sources
        </summary>
        <div className="px-4 pb-4 space-y-4 text-sm text-slate-200">
          <div>
            <h5 className="font-semibold text-slate-100 mb-1">What this may give you</h5>
            <p className="leading-relaxed">{route.provenance.claim}</p>
          </div>
          <div>
            <h5 className="font-semibold text-slate-100 mb-1">Why this matched</h5>
            <p className="leading-relaxed">{route.provenance.why_matched}</p>
          </div>
          <div>
            <h5 className="font-semibold text-slate-100 mb-1">Evidence used</h5>
            <ul className="list-disc pl-5 space-y-1">
              {route.provenance.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
            </ul>
          </div>
          <div>
            <h5 className="font-semibold text-slate-100 mb-1">About this option</h5>
            <p className="leading-relaxed">{route.summary}</p>
          </div>
          <div className="space-y-1">
            <h5 className="font-semibold text-slate-100">Sources</h5>
            <a href={route.primary_source.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sky-300 hover:text-sky-200 underline">
              {route.primary_source.title} <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </a>
            {(route.related_sources ?? []).map((s) => (
              <div key={s.url}>
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sky-300 hover:text-sky-200 underline">
                  {s.title} <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                </a>
              </div>
            ))}
            <p className="text-slate-300">Checked by a person: {shortDate(route.primary_source.verified_at)}</p>
            <p className="text-slate-300 inline-flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
              {check
                ? `Source last checked automatically: ${shortDate(check.checked_at)}, page ${check.reachable ? 'online' : `offline (HTTP ${check.http_status})`}` +
                  (check.listed_on_apple_index != null ? `, ${check.listed_on_apple_index ? 'still listed' : 'not listed'} on Apple's program list` : '')
                : 'Automatic source check: not run yet here'}
            </p>
          </div>
        </div>
      </details>
    </article>
  );
}

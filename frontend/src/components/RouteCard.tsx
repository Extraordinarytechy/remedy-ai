import { useState } from 'react';
import { AlertTriangle, Check, CheckCircle2, Copy, Download, ExternalLink, Info, RefreshCw } from 'lucide-react';
import type { MatchedRoute, NormalizedCase } from '../types';
import { ROUTE_TYPE_LABEL, STATUS_LABEL, TONE_CLASSES, shortDate } from './labels';

interface Props {
  route: MatchedRoute;
  c: NormalizedCase;
  onDownload: () => void;
  downloading: boolean;
}

export function RouteCard({ route, c, onDownload, downloading }: Props) {
  const [copied, setCopied] = useState(false);
  const status = STATUS_LABEL[route.status];
  const check = route.source_check;

  const copyLetter = async () => {
    const letter =
      `To: ${route.provider}\nSubject: Claim for ${c.product_name}\n\n` +
      `I bought my ${c.product_name} on ${c.purchase_date}. On ${c.failure_date} it developed this fault: "${c.defect_description}".\n\n` +
      `Based on the published terms of ${route.title} (${route.primary_source.url}), I believe it may qualify for a remedy, subject to your inspection and verification. ` +
      `I can provide proof of purchase, photos of the fault and payment records.\n\nPlease confirm receipt and tell me the next step.`;
    await navigator.clipboard.writeText(letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <article className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-5 shadow-lg" aria-labelledby={`route-${route.route_id}`}>
      <header className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${TONE_CLASSES[status.tone]}`}>{status.text}</span>
            <span className="text-xs text-slate-400">{ROUTE_TYPE_LABEL[route.route_type]}</span>
          </div>
          <h3 id={`route-${route.route_id}`} className="text-lg font-bold text-white">{route.title}</h3>
          <p className="text-xs text-slate-400">{route.provider}</p>
        </div>
        <button
          onClick={onDownload}
          disabled={downloading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs shadow-md transition disabled:opacity-50 shrink-0"
        >
          <Download className="w-4 h-4" aria-hidden="true" />
          {downloading ? 'Preparing PDF...' : 'Download claim PDF'}
        </button>
      </header>

      <p className="text-sm text-slate-200 leading-relaxed">{route.provenance.claim}</p>

      <div className="space-y-4 text-xs">
        <section>
          <h4 className="text-slate-300 font-semibold mb-1">Why this matched</h4>
          <p className="text-slate-200 bg-slate-950/70 p-3 rounded-lg border border-slate-800 leading-relaxed">{route.provenance.why_matched}</p>
        </section>

        <section>
          <h4 className="text-slate-300 font-semibold mb-1">Evidence used</h4>
          <ul className="space-y-1">
            {route.provenance.evidence.map((ev, i) => (
              <li key={i} className="flex items-start gap-2 text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{ev}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h4 className="text-slate-300 font-semibold mb-1">What you will need</h4>
          <ul className="space-y-1">
            {route.provenance.conditions.map((cond, i) => (
              <li key={i} className="flex items-start gap-2 text-slate-300">
                <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{cond}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h4 className="text-amber-300 font-semibold mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" /> What could stop this
          </h4>
          <ul className="space-y-1">
            {route.provenance.exceptions.map((exc, i) => (
              <li key={i} className="text-amber-100/90 bg-amber-500/5 p-2 rounded border border-amber-500/15">{exc}</li>
            ))}
          </ul>
        </section>

        <section className="bg-slate-950/70 rounded-lg p-3 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-slate-300 font-semibold">Next step</h4>
            <button onClick={copyLetter} className="inline-flex items-center gap-1.5 text-sky-300 hover:text-sky-200 font-medium">
              {copied ? <Check className="w-3.5 h-3.5" aria-hidden="true" /> : <Copy className="w-3.5 h-3.5" aria-hidden="true" />}
              {copied ? 'Copied' : 'Copy a draft claim letter'}
            </button>
          </div>
          <p className="text-slate-200 leading-relaxed">{route.recommended_action}</p>
        </section>

        <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400 pt-1">
          <a href={route.primary_source.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sky-300 hover:text-sky-200 underline">
            Read the source <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </a>
          <span>Checked by a person: {shortDate(route.primary_source.verified_at)}</span>
          {check ? (
            <span className="inline-flex items-center gap-1">
              <RefreshCw className="w-3 h-3" aria-hidden="true" />
              Source Watch: {shortDate(check.checked_at)}, page {check.reachable ? 'reachable' : `unreachable (HTTP ${check.http_status})`}
              {check.listed_on_apple_index != null && `, ${check.listed_on_apple_index ? 'listed' : 'not listed'} on Apple's index`}
            </span>
          ) : (
            <span>Source Watch: not run yet in this environment</span>
          )}
        </footer>
      </div>
    </article>
  );
}

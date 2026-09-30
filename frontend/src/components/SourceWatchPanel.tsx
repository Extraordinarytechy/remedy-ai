import { ExternalLink, RefreshCw } from 'lucide-react';
import type { SourcesResponse } from '../types';
import { shortDate } from './labels';

export function SourceWatchPanel({ data }: { data: SourcesResponse | null }) {
  if (!data) return null;
  const idx = data.apple_index;
  return (
    <section aria-labelledby="sw-heading" className="bg-slate-900/70 border border-slate-700 rounded-2xl p-5 sm:p-6 space-y-4">
      <div className="space-y-1">
        <h2 id="sw-heading" className="font-bold text-white text-lg flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-emerald-400" aria-hidden="true" />
          Where the answers come from (Source Watch)
        </h2>
        <p className="text-sm text-slate-300 max-w-3xl">
          Every answer comes from one of these official pages. A person checked each one, and RemedyAI re-checks them
          automatically every day. If a page disappears, or an Apple program leaves Apple's list, that option is marked
          "check it first" instead of being shown as a match.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <caption className="sr-only">Official sources and their latest checks</caption>
          <thead className="text-slate-300">
            <tr>
              <th scope="col" className="py-2 pr-3 font-medium">Source</th>
              <th scope="col" className="py-2 pr-3 font-medium">Checked by a person</th>
              <th scope="col" className="py-2 pr-3 font-medium">Last automatic check</th>
              <th scope="col" className="py-2 font-medium">Result</th>
            </tr>
          </thead>
          <tbody className="text-slate-100">
            {data.sources.map((s) => {
              const w = s.watch ?? {};
              const result = !w.checked_at
                ? 'Not run yet'
                : w.reachable === false
                  ? `Page offline (HTTP ${w.http_status})`
                  : w.listed_on_apple_index === false
                    ? "Online, but not on Apple's program list"
                    : w.listed_on_apple_index
                      ? "Online, on Apple's program list"
                      : 'Online';
              const bad = w.reachable === false || w.listed_on_apple_index === false;
              return (
                <tr key={s.id} className="border-t border-slate-800 align-top">
                  <td className="py-2.5 pr-3">
                    <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="text-sky-300 hover:text-sky-200 underline inline-flex items-center gap-1">
                      {s.program_name} <ExternalLink className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                    </a>
                  </td>
                  <td className="py-2.5 pr-3 whitespace-nowrap">{shortDate(s.human_verified_at)}</td>
                  <td className="py-2.5 pr-3 whitespace-nowrap">{shortDate(w.checked_at)}</td>
                  <td className={`py-2.5 ${bad ? 'text-amber-200 font-semibold' : 'text-slate-100'}`}>{result}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {idx && idx.http_status === 200 && (
        <div className="space-y-1 text-sm text-slate-300">
          <p>
            Apple's service-program list on {shortDate(idx.checked_at)} had {idx.titles.length} programs.
            {idx.added_since_last_check.length > 0 && ` New since the previous check: ${idx.added_since_last_check.join('; ')}.`}
            {idx.removed_since_last_check.length > 0 && ` Removed since the previous check: ${idx.removed_since_last_check.join('; ')}.`}
          </p>
          {idx.uncovered_service_programs && (
            idx.uncovered_service_programs.length > 0 ? (
              <p className="text-amber-200 font-medium">
                Not covered by RemedyAI yet (a person must verify these first): {idx.uncovered_service_programs.join('; ')}.
              </p>
            ) : (
              <p>Every repair program on Apple's list is covered by RemedyAI.</p>
            )
          )}
          {idx.uncovered_recall_or_exchange_programs && idx.uncovered_recall_or_exchange_programs.length > 0 && (
            <p className="text-slate-400">
              Recall and exchange programs are not covered yet ({idx.uncovered_recall_or_exchange_programs.length} on the
              list). See <a className="underline text-sky-300" href={idx.url}>Apple's list</a> for those.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

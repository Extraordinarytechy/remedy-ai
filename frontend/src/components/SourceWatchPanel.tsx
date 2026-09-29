import { ExternalLink, RefreshCw } from 'lucide-react';
import type { SourcesResponse } from '../types';
import { shortDate } from './labels';

export function SourceWatchPanel({ data }: { data: SourcesResponse | null }) {
  if (!data) return null;
  const idx = data.apple_index;
  return (
    <section aria-labelledby="sw-heading" className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="sw-heading" className="font-semibold text-white text-sm flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-emerald-400" aria-hidden="true" />
          Source Watch: every source is re-checked daily
        </h2>
        <p className="text-[11px] text-slate-400">
          A route whose source page disappears or leaves Apple's index is downgraded to "re-verify first".
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <caption className="sr-only">Primary sources and their latest automated check</caption>
          <thead className="text-slate-400">
            <tr>
              <th scope="col" className="py-1.5 pr-3 font-medium">Source</th>
              <th scope="col" className="py-1.5 pr-3 font-medium">Checked by a person</th>
              <th scope="col" className="py-1.5 pr-3 font-medium">Last automated check</th>
              <th scope="col" className="py-1.5 font-medium">Result</th>
            </tr>
          </thead>
          <tbody className="text-slate-200">
            {data.sources.map((s) => {
              const w = s.watch ?? {};
              const result = !w.checked_at
                ? 'Not run yet'
                : w.reachable === false
                  ? `Unreachable (HTTP ${w.http_status})`
                  : w.listed_on_apple_index === false
                    ? "Not on Apple's index"
                    : w.listed_on_apple_index
                      ? "Reachable, on Apple's index"
                      : 'Reachable';
              const bad = w.reachable === false || w.listed_on_apple_index === false;
              return (
                <tr key={s.id} className="border-t border-slate-800">
                  <td className="py-2 pr-3">
                    <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="text-sky-300 hover:text-sky-200 underline inline-flex items-center gap-1">
                      {s.program_name} <ExternalLink className="w-3 h-3" aria-hidden="true" />
                    </a>
                  </td>
                  <td className="py-2 pr-3 font-mono">{shortDate(s.human_verified_at)}</td>
                  <td className="py-2 pr-3 font-mono">{shortDate(w.checked_at)}</td>
                  <td className={`py-2 ${bad ? 'text-amber-300 font-semibold' : 'text-slate-200'}`}>{result}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {idx && idx.http_status === 200 && (
        <p className="text-[11px] text-slate-400">
          Apple's service-program index on {shortDate(idx.checked_at)} listed {idx.titles.length} programs.
          {idx.added_since_last_check.length > 0 && ` New since the previous check: ${idx.added_since_last_check.join('; ')}.`}
          {idx.removed_since_last_check.length > 0 && ` Removed since the previous check: ${idx.removed_since_last_check.join('; ')}.`}
        </p>
      )}
    </section>
  );
}

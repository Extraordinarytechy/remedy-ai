import { ArrowUpRight } from 'lucide-react';
import type { SourceEntry, SourcesResponse } from '../types';
import { shortDate } from './labels';

function resultOf(s: SourceEntry): { text: string; bad: boolean } {
  const w = s.watch ?? {};
  if (!w.checked_at) return { text: 'Not checked yet', bad: false };
  if (w.reachable === false) return { text: `Page offline (HTTP ${w.http_status})`, bad: true };
  if (w.key_text_present === false) return { text: 'Key wording missing', bad: true };
  if (w.listed_on_apple_index === false) return { text: "Not on Apple's list", bad: true };
  if (w.apple_index_ok === false) return { text: "Apple's list could not be read", bad: true };
  const changed = (w.last_changed_at ?? '').slice(0, 10);
  const verified = (s.human_verified_at ?? '').slice(0, 10);
  if (changed && verified && changed > verified) return { text: `Changed ${shortDate(changed)}, re-verify`, bad: true };
  if (w.listed_on_apple_index) return { text: "Online, on Apple's list", bad: false };
  return { text: 'Online', bad: false };
}

/** One-line status for the page: how many sources, when last checked, anything wrong. */
export function sourcesSummary(data: SourcesResponse | null) {
  if (!data) return null;
  const checked = data.sources.map((s) => s.watch?.checked_at).filter(Boolean).sort() as string[];
  const issues = data.sources.filter((s) => resultOf(s).bad && s.watch?.listed_on_apple_index !== false).length;
  return { count: data.sources.length, last: checked.length ? checked[checked.length - 1] : null, issues };
}

/** Full Source Watch table, shown in a dialog. */
export function SourcesTable({ data }: { data: SourcesResponse }) {
  const idx = data.apple_index;
  return (
    <div className="space-y-5">
      <p className="text-muted">
        Every answer comes from one of these official pages. Each was verified before it went live, and Source Watch re-checks
        them automatically every day. If a page disappears, its text changes after it was verified or Apple drops a program,
        that option is marked "check it first" instead of being shown as a match.
      </p>
      <div className="overflow-x-auto rounded-2xl border border-line">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Official sources and their latest checks</caption>
          <thead className="bg-subtle text-muted">
            <tr>
              <th scope="col" className="px-4 py-2.5 font-medium">Source</th>
              <th scope="col" className="px-4 py-2.5 font-medium whitespace-nowrap">Verified</th>
              <th scope="col" className="px-4 py-2.5 font-medium whitespace-nowrap">Last automatic check</th>
              <th scope="col" className="px-4 py-2.5 font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {data.sources.map((s) => {
              const r = resultOf(s);
              return (
                <tr key={s.id} className="border-t border-line align-top">
                  <td className="px-4 py-3">
                    <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="link inline-flex items-start gap-1">
                      {s.program_name} <ArrowUpRight className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                    </a>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-muted">{shortDate(s.human_verified_at)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-muted">{shortDate(s.watch?.checked_at)}</td>
                  <td className={`px-4 py-3 ${r.bad ? 'font-semibold text-warn-ink' : 'text-ink'}`}>{r.text}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {idx && idx.http_status === 200 && (
        <div className="space-y-1.5 text-sm text-muted">
          <p>
            Apple's service-program list on {shortDate(idx.checked_at)} had {idx.titles.length} programs.
            {idx.added_since_last_check.length > 0 && ` New since the previous check: ${idx.added_since_last_check.join('; ')}.`}
            {idx.removed_since_last_check.length > 0 && ` Removed since the previous check: ${idx.removed_since_last_check.join('; ')}.`}
          </p>
          {idx.uncovered_service_programs && (
            idx.uncovered_service_programs.length > 0 ? (
              <p className="font-medium text-warn-ink">Not covered yet (each needs to be verified first): {idx.uncovered_service_programs.join('; ')}.</p>
            ) : (
              <p>Every repair program on Apple's list is covered.</p>
            )
          )}
          {idx.uncovered_recall_or_exchange_programs && idx.uncovered_recall_or_exchange_programs.length > 0 && (
            <p>
              Recall and exchange programs are not covered yet ({idx.uncovered_recall_or_exchange_programs.length} on the list).
              See <a className="link" href={idx.url} target="_blank" rel="noopener noreferrer">Apple's list</a> for those.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

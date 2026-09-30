import { BadgeCheck, CreditCard, Landmark, ShieldCheck, Sparkles, Wrench } from 'lucide-react';
import type { ComponentType } from 'react';

/*
 * "What RemedyAI covers today", built at build time from backend/knowledge/*.json: the same
 * records the engine uses. A product or country appears here only if a verified record exists.
 */
interface KnowledgeRecord {
  id: string;
  category: string;
  issuer_or_brand?: string;
  program_name: string;
  source_url: string;
  verified_at?: string;
  coverage_summary?: string;
  coverage_region?: string;
  listed_on_apple_service_programs_index?: boolean;
}

const records = Object.values(
  import.meta.glob<KnowledgeRecord>('../../../backend/knowledge/**/*.json', { eager: true, import: 'default' }),
);

const GROUPS: { category: string; title: string; who: string; icon: ComponentType<{ className?: string }> }[] = [
  { category: 'manufacturer_warranty', title: "Maker's warranty", who: 'Apple', icon: ShieldCheck },
  { category: 'manufacturer_service_program', title: 'Free repair programs', who: 'Apple', icon: Wrench },
  { category: 'card_benefit', title: 'Card benefits', who: 'Any brand', icon: CreditCard },
  { category: 'statutory_consumer_law', title: 'Consumer law', who: 'Any brand', icon: Landmark },
];

// Planned sources. None of these is used until a person has verified its official page.
const NEXT = [
  'New Apple repair programs as Apple lists them (Source Watch flags them daily)',
  'Samsung and Google repair programs',
  'Mastercard and American Express warranty benefits',
  'EU two-year legal guarantee',
  'Consumer law in India, the US states, Canada and Australia',
];

export function CoveragePanel() {
  return (
    <section id="coverage" aria-labelledby="coverage-heading" className="space-y-4 scroll-mt-24">
      <div className="space-y-1">
        <h2 id="coverage-heading" className="text-xl font-bold text-white">What RemedyAI covers today</h2>
        <p className="text-slate-300 max-w-3xl">
          Every option below comes from an official page a person has checked. <b className="text-slate-100">Apple</b> devices
          get Apple's own warranty and repair programs. <b className="text-slate-100">Any brand</b> can match the card and
          consumer-law options. If your product isn't covered, RemedyAI tells you so instead of guessing.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {GROUPS.map((g) => {
          const items = records.filter((r) => r.category === g.category);
          if (!items.length) return null;
          const Icon = g.icon;
          return (
            <div key={g.category} className="bg-slate-900/70 border border-slate-700 rounded-xl p-4 space-y-3 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <Icon className="w-5 h-5 text-sky-300 shrink-0" /> {g.title}
                </h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-100 whitespace-nowrap">{g.who}</span>
              </div>
              <ul className="space-y-2.5">
                {items.map((r) => {
                  const ended = r.listed_on_apple_service_programs_index === false;
                  return (
                    <li key={r.id} className={`text-sm ${ended ? 'text-slate-400' : 'text-slate-200'}`}>
                      <span className="flex items-start gap-2">
                        <BadgeCheck className={`w-4 h-4 shrink-0 mt-0.5 ${ended ? 'text-slate-500' : 'text-emerald-400'}`} aria-hidden="true" />
                        <span>
                          {r.coverage_summary ?? r.program_name}
                          {r.coverage_region && <span className="text-slate-400"> · {r.coverage_region}</span>}
                          {ended && <span className="ml-1 text-xs font-semibold text-amber-200">(ended)</span>}
                          {' '}
                          <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-sky-300 underline whitespace-nowrap">
                            source
                          </a>
                        </span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      <div className="bg-slate-900/40 border border-dashed border-slate-600 rounded-xl p-4 space-y-2">
        <h3 className="font-semibold text-slate-100 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-200" aria-hidden="true" /> Coming next
        </h3>
        <p className="text-sm text-slate-300">
          RemedyAI is expanding one verified source at a time. These are planned and <b>not used yet</b>:
        </p>
        <ul className="list-disc pl-5 space-y-1 text-sm text-slate-300">
          {NEXT.map((n) => <li key={n}>{n}</li>)}
        </ul>
      </div>
    </section>
  );
}

import { useState, type ComponentType } from 'react';
import { ArrowUpRight, ChevronDown, CreditCard, Landmark, ShieldCheck, Sparkles, Wrench } from 'lucide-react';
import { Modal } from './ui';

/*
 * "What RemedyAI covers today", built at build time from backend/knowledge/*.json: the same
 * records the engine uses. A product or country appears here only if a verified record exists.
 */
interface KnowledgeRecord {
  id: string;
  category: string;
  program_name: string;
  source_url: string;
  coverage_summary?: string;
  coverage_region?: string;
  listed_on_apple_service_programs_index?: boolean;
}

const records = Object.values(
  import.meta.glob<KnowledgeRecord>('../../../backend/knowledge/**/*.json', { eager: true, import: 'default' }),
);

type Icon = ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
const GROUPS: { category: string; title: string; who: string; teaser: string; icon: Icon }[] = [
  { category: 'manufacturer_warranty', title: "Maker's warranty", who: 'Apple', teaser: 'New iPhone, iPad and more, first year (U.S.)', icon: ShieldCheck },
  { category: 'manufacturer_service_program', title: 'Free repair programs', who: 'Apple', teaser: 'Known faults Apple repairs for free', icon: Wrench },
  { category: 'card_benefit', title: 'Card benefits', who: 'Any brand', teaser: 'Visa Infinite adds a year (U.S.)', icon: CreditCard },
  { category: 'statutory_consumer_law', title: 'Consumer law', who: 'Any brand', teaser: 'Up to 6 years to claim (UK)', icon: Landmark },
];

// Planned sources. None is used until a person has verified its official page.
export const COMING_NEXT = [
  'New Apple repair programs as Apple lists them (Source Watch flags them daily)',
  'Samsung and Google repair programs',
  'Mastercard and American Express warranty benefits',
  'EU two-year legal guarantee',
  'Consumer law in India, the US states, Canada and Australia',
];

export function CoveragePanel() {
  const [open, setOpen] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState(false);

  return (
    <section id="coverage" aria-labelledby="coverage-heading" className="scroll-mt-24 space-y-8">
      <div className="max-w-2xl space-y-3">
        <p className="eyebrow">Coverage</p>
        <h2 id="coverage-heading" className="text-3xl font-semibold tracking-tight sm:text-4xl">What RemedyAI covers today</h2>
        <p className="text-lg text-muted">
          Apple devices get Apple's own warranty and repair programs. Any brand can match the card and consumer-law options.
          Every option comes from an official page a person has checked.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {GROUPS.map((g) => {
          const items = records.filter((r) => r.category === g.category);
          if (!items.length) return null;
          const expanded = open === g.category;
          const Icon = g.icon;
          const panelId = `coverage-${g.category}`;
          return (
            <div key={g.category} className={`card flex flex-col p-5 transition-shadow ${expanded ? 'shadow-lg sm:col-span-2 lg:col-span-2' : 'hover:shadow-md'}`}>
              <div className="flex items-start justify-between gap-3">
                <span className="inline-flex size-10 items-center justify-center rounded-2xl bg-accent-soft text-accent-text">
                  <Icon className="size-5" aria-hidden />
                </span>
                <span className="chip">{g.who}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold">{g.title}</h3>
              <p className="mt-1 text-sm text-muted">{g.teaser}</p>
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={panelId}
                onClick={() => setOpen(expanded ? null : g.category)}
                className="mt-4 inline-flex items-center gap-1.5 self-start text-sm font-semibold text-accent-text hover:underline"
              >
                {expanded ? 'Hide details' : `${items.length} ${items.length === 1 ? 'source' : 'sources'} · details`}
                <ChevronDown className={`size-4 transition-transform ${expanded ? 'rotate-180' : ''}`} aria-hidden="true" />
              </button>
              {expanded && (
                <ul id={panelId} className="mt-4 space-y-3 border-t border-line pt-4">
                  {items.map((r) => {
                    const ended = r.listed_on_apple_service_programs_index === false;
                    return (
                      <li key={r.id} className={`text-sm leading-relaxed ${ended ? 'text-faint' : 'text-ink'}`}>
                        {r.coverage_summary ?? r.program_name}
                        {r.coverage_region && <span className="text-faint"> · {r.coverage_region}</span>}
                        {ended && <span className="ml-1.5 rounded-full bg-warn-soft px-2 py-0.5 text-xs font-semibold text-warn-ink">Ended</span>}
                        <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="link ml-1.5 inline-flex items-center gap-0.5 whitespace-nowrap">
                          Source <ArrowUpRight className="size-3.5" aria-hidden="true" />
                        </a>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border border-dashed border-line-strong px-5 py-4 text-sm text-muted">
        <Sparkles className="size-4 text-accent-text" aria-hidden="true" />
        <span>Expanding one verified source at a time: Samsung, Google, Mastercard, American Express, the EU guarantee and more.</span>
        <button type="button" onClick={() => setRoadmap(true)} className="link">See the roadmap</button>
      </div>

      <Modal open={roadmap} onClose={() => setRoadmap(false)} title="Coming next">
        <p className="text-muted">These are planned and <b className="text-ink">not used yet</b>. Each one goes live only after a person has verified its official page.</p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-ink">
          {COMING_NEXT.map((n) => <li key={n}>{n}</li>)}
        </ul>
      </Modal>
    </section>
  );
}

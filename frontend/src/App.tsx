import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, Coffee, CreditCard, Info, ShieldAlert, ShieldCheck, Smartphone, Tv } from 'lucide-react';
import { api } from './api';
import type { NormalizedCase, RemedyEvaluation, SourcesResponse } from './types';
import { EvidencePanel } from './components/EvidencePanel';
import { RouteCard } from './components/RouteCard';
import { SourceWatchPanel } from './components/SourceWatchPanel';
import { CheckForm } from './components/CheckForm';

const DEMOS = [
  {
    key: 'case1_apple_iphone14plus',
    icon: Smartphone,
    tag: 'Manufacturer program',
    title: 'iPhone 14 Plus, rear camera',
    blurb: 'Out of warranty after 2.8 years. Apple runs a free repair program for exactly this fault.',
  },
  {
    key: 'case2_visa_infinite_sony',
    icon: CreditCard,
    tag: 'Card benefit',
    title: 'Headphones bought with Visa Infinite',
    blurb: 'Hinge cracked at 18 months. The card can add a year to the manufacturer warranty.',
  },
  {
    key: 'case3_uk_samsung_tv',
    icon: Tv,
    tag: 'Consumer law',
    title: 'TV bought in the UK',
    blurb: 'Screen fault at 3 years. UK law gives up to 6 years to claim against the retailer.',
  },
  {
    key: 'case4_unknown_unsupported',
    icon: Coffee,
    tag: 'No match',
    title: 'Espresso machine, paid cash',
    blurb: 'Nothing in the verified sources covers it, so RemedyAI says so instead of guessing.',
  },
] as const;

type Mode = { kind: 'demo'; key: string } | { kind: 'own'; case: NormalizedCase | null };

export default function App() {
  const [fixtures, setFixtures] = useState<Record<string, NormalizedCase> | null>(null);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: 'demo', key: DEMOS[0].key });
  const [evaluation, setEvaluation] = useState<RemedyEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const activeCase: NormalizedCase | null =
    mode.kind === 'demo' ? (fixtures?.[mode.key] ?? null) : mode.case;

  useEffect(() => {
    api.fixtures().then(setFixtures).catch((e: Error) => { setError(e.message); setLoading(false); });
    api.sources().then(setSources).catch(() => setSources(null));
  }, []);

  const evaluate = async (c: NormalizedCase) => {
    setLoading(true);
    setError(null);
    setEvaluation(null);
    try {
      setEvaluation(await api.evaluate(c));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mode.kind === 'demo' && activeCase) evaluate(activeCase);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, fixtures]);

  const downloadPdf = async () => {
    if (!activeCase || !evaluation) return;
    setDownloading(true);
    try {
      const blob = await api.claimPdf(activeCase, evaluation);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `RemedyAI_Claim_${activeCase.case_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center" aria-hidden="true">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight text-white">RemedyAI</p>
              <p className="text-xs text-slate-400">Find the free repair or refund you may still be owed after the warranty ends</p>
            </div>
          </div>
          <nav className="flex items-center gap-4 text-xs" aria-label="Project links">
            <a href="#sw-heading" className="text-slate-300 hover:text-white underline">Where the answers come from</a>
            <a href="https://github.com/Extraordinarytechy/remedy-ai" className="text-slate-300 hover:text-white underline">Source code</a>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <section className="space-y-3 max-w-3xl">
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Your warranty ended. That does not always mean you pay.
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            Manufacturers run free repair programs for known faults, some credit cards extend warranties, and consumer law can
            outlast both. RemedyAI checks your case against the published source for each of these, shows exactly why it
            matched and what could stop it, and prepares a claim you can send. If no source covers you, it says so.
          </p>
        </section>

        <section aria-labelledby="demo-heading" className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="demo-heading" className="text-base font-bold text-white">Try an example, or check your own product</h2>
            <button
              onClick={() => { setMode({ kind: 'own', case: null }); setEvaluation(null); setError(null); setLoading(false); }}
              className={`text-xs px-3 py-1.5 rounded-md border ${mode.kind === 'own' ? 'bg-sky-600 border-sky-500 text-white' : 'bg-slate-800 border-slate-600 text-slate-100 hover:bg-slate-700'}`}
            >
              Check my own product
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {DEMOS.map((d) => {
              const selected = mode.kind === 'demo' && mode.key === d.key;
              const Icon = d.icon;
              return (
                <button
                  key={d.key}
                  onClick={() => setMode({ kind: 'demo', key: d.key })}
                  aria-pressed={selected}
                  className={`text-left p-4 rounded-xl border transition ${selected ? 'bg-sky-950/40 border-sky-500 ring-1 ring-sky-500' : 'bg-slate-900/60 border-slate-800 hover:border-slate-600'}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Icon className="w-5 h-5 text-sky-300" aria-hidden="true" />
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-200">{d.tag}</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">{d.title}</h3>
                  <p className="text-xs text-slate-400 mt-1">{d.blurb}</p>
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500">Examples use sample receipts and photo descriptions, labelled as sample data.</p>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5 space-y-6">
            {mode.kind === 'own' && (
              <CheckForm
                busy={loading}
                onSubmit={(c) => { setMode({ kind: 'own', case: c }); evaluate(c); }}
              />
            )}
            {activeCase && <EvidencePanel c={activeCase} />}
          </div>

          <div className="lg:col-span-7 space-y-6" aria-live="polite">
            {error ? (
              <div role="alert" className="bg-slate-900/80 border border-amber-500/40 rounded-xl p-6 space-y-2">
                <p className="flex items-center gap-2 text-amber-300 font-semibold text-sm">
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" /> Something went wrong
                </p>
                <p className="text-xs text-slate-300">{error}</p>
                <p className="text-xs text-slate-400">No result is shown, because RemedyAI only reports what its engine actually determined.</p>
              </div>
            ) : loading ? (
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-12 text-center">
                <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" aria-hidden="true"></div>
                <p className="text-sm text-slate-300 mt-3">Checking the published sources...</p>
              </div>
            ) : evaluation && evaluation.has_coverage && activeCase ? (
              <>
                <p className="text-[11px] text-slate-400">
                  Deadlines measured as of {evaluation.evaluation_date}. {evaluation.matched_routes.length} route(s) found.
                </p>
                {evaluation.matched_routes.map((r) => (
                  <RouteCard key={r.route_id} route={r} c={activeCase} onDownload={downloadPdf} downloading={downloading} />
                ))}
                <Notes notes={evaluation.notes} />
              </>
            ) : evaluation ? (
              <div className="bg-slate-900/80 border border-rose-500/40 rounded-xl p-6 space-y-4">
                <p className="flex items-center gap-2 text-rose-300 font-bold text-sm">
                  <ShieldAlert className="w-5 h-5" aria-hidden="true" />
                  {evaluation.unmatched_reason?.startsWith('INVALID INPUT') ? 'Please check the dates' : 'No verified coverage found'}
                </p>
                <p className="text-xs text-slate-300">{evaluation.unmatched_reason}</p>
                <Notes notes={evaluation.notes} />
                <div>
                  <p className="font-semibold text-slate-200 text-xs mb-1">What you can still try</p>
                  <ul className="space-y-1.5">
                    {evaluation.next_steps.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                        <ArrowRight className="w-3.5 h-3.5 text-rose-300 shrink-0 mt-0.5" aria-hidden="true" /> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : mode.kind === 'own' ? (
              <div className="bg-slate-900/50 border border-dashed border-slate-700 rounded-xl p-8 text-sm text-slate-400">
                Fill in the form to check your product. Results appear here.
              </div>
            ) : null}
          </div>
        </div>

        <SourceWatchPanel data={sources} />
      </main>

      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-400 space-y-1 px-4">
        <p className="max-w-4xl mx-auto">
          RemedyAI prepares claims. It is not legal advice and does not guarantee a repair, replacement or refund. The
          manufacturer, card issuer or retailer makes the final decision.
        </p>
        <p className="text-[11px]">Built for AWS Zero to Shipped on AWS Lambda, Amazon Textract, Amazon Bedrock, DynamoDB, S3 and CloudFront.</p>
      </footer>
    </div>
  );
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <section className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 space-y-1">
      <h3 className="text-xs font-semibold text-slate-200">Sources checked that did not apply</h3>
      <ul className="space-y-1">
        {notes.map((n, i) => (
          <li key={i} className="flex items-start gap-2 text-[11px] text-slate-300">
            <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" aria-hidden="true" /> {n}
          </li>
        ))}
      </ul>
    </section>
  );
}

import { useEffect, useRef, useState, type RefObject } from 'react';
import {
  AlertTriangle, ArrowRight, CalendarDays, CheckCircle2, Coffee, CreditCard, Info, Lock, Search, ShieldAlert, ShieldCheck, Smartphone, Tv,
} from 'lucide-react';
import { api } from './api';
import type { CaseCheck, NormalizedCase, RemedyEvaluation, SourcesResponse } from './types';
import { EvidencePanel } from './components/EvidencePanel';
import { RouteCard } from './components/RouteCard';
import { SourceWatchPanel } from './components/SourceWatchPanel';
import { CheckForm } from './components/CheckForm';
import { daysLeftText, humanDate, verdictFor } from './components/labels';

const REPO_URL = 'https://github.com/Extraordinarytechy/remedy-ai';

// Set to true once the AWS account has an AI services opt-out policy for Amazon Textract.
const TEXTRACT_OPTED_OUT = false;

const DEMOS = [
  {
    key: 'case1_apple_iphone14plus',
    icon: Smartphone,
    tag: 'Free repair program',
    title: 'iPhone 14 Plus, rear camera',
    blurb: 'Out of warranty after nearly 3 years. Apple runs a free repair program for this fault.',
  },
  {
    key: 'case2_visa_infinite_sony',
    icon: CreditCard,
    tag: 'Card benefit',
    title: 'Headphones paid with Visa Infinite',
    blurb: 'Hinge cracked at 18 months. The card can add a year to the warranty.',
  },
  {
    key: 'case3_uk_samsung_tv',
    icon: Tv,
    tag: 'Consumer law',
    title: 'TV bought in the UK',
    blurb: 'Screen fault at 3 years. UK law gives up to 6 years to claim from the store.',
  },
  {
    key: 'case4_unknown_unsupported',
    icon: Coffee,
    tag: 'No match',
    title: 'Espresso machine, paid cash',
    blurb: "No verified source covers it, so RemedyAI says so instead of guessing.",
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
  const verdictRef = useRef<HTMLHeadingElement>(null);
  const moveFocus = useRef(false);

  const activeCase: NormalizedCase | null = mode.kind === 'demo' ? (fixtures?.[mode.key] ?? null) : mode.case;

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

  // Move keyboard/screen-reader focus to the answer when a user-started check finishes.
  useEffect(() => {
    if (evaluation && moveFocus.current) {
      verdictRef.current?.focus();
      moveFocus.current = false;
    }
  }, [evaluation]);

  const startOwn = () => {
    setMode({ kind: 'own', case: null });
    setEvaluation(null);
    setError(null);
    setLoading(false);
    setTimeout(() => document.getElementById('check-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  };

  const confirmCheck = (id: string) => {
    if (mode.kind !== 'own' || !mode.case) return;
    const c = { ...mode.case, confirmed_checks: [...new Set([...(mode.case.confirmed_checks ?? []), id])] };
    setMode({ kind: 'own', case: c });
    evaluate(c);
  };

  const downloadPdf = async () => {
    if (!activeCase) return;
    setDownloading(true);
    try {
      const blob = await api.claimPdf(activeCase);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `RemedyAI_Claim_${activeCase.case_id.replace(/[^A-Za-z0-9_-]/g, '')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans text-[15px] [overflow-wrap:anywhere]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[60] focus:bg-sky-600 focus:text-white focus:px-3 focus:py-2 focus:rounded">
        Skip to content
      </a>
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center" aria-hidden="true">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <p className="text-lg font-bold tracking-tight text-white">RemedyAI</p>
          </div>
          <nav className="flex items-center gap-4 text-sm" aria-label="Site">
            <a href="#sw-heading" className="text-slate-200 hover:text-white underline underline-offset-2">Sources</a>
            <a href="#privacy" className="text-slate-200 hover:text-white underline underline-offset-2">Privacy</a>
            <a href={REPO_URL} className="text-slate-200 hover:text-white underline underline-offset-2">Source code</a>
          </nav>
        </div>
      </header>

      <main id="main" className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
        <section className="space-y-4 max-w-3xl">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Your warranty ended. You may still get a free repair.
          </h1>
          <p className="text-base sm:text-lg text-slate-200 leading-relaxed">
            Makers run free repair programs for known faults, some cards extend warranties, and consumer law can last longer
            than both. Tell RemedyAI what broke. It checks official sources, tells you what to do next, and prepares a claim.
            If nothing covers you, it says so.
          </p>
          <div className="flex flex-wrap items-center gap-4 pt-1">
            <button
              onClick={startOwn}
              className="inline-flex items-center gap-2 min-h-12 px-6 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-base shadow-lg"
            >
              <Search className="w-5 h-5" aria-hidden="true" /> Check my product
            </button>
            <span className="text-sm text-slate-300">Free. No sign-up. About 2 minutes.</span>
          </div>
        </section>

        <section aria-labelledby="demo-heading" className="space-y-3">
          <h2 id="demo-heading" className="text-base font-semibold text-slate-100">Or try an example</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {DEMOS.map((d) => {
              const selected = mode.kind === 'demo' && mode.key === d.key;
              const Icon = d.icon;
              return (
                <button
                  key={d.key}
                  onClick={() => { moveFocus.current = true; setMode({ kind: 'demo', key: d.key }); }}
                  aria-pressed={selected}
                  className={`min-w-0 text-left p-4 rounded-xl border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${selected ? 'bg-sky-950/50 border-sky-400 ring-1 ring-sky-400' : 'bg-slate-900/70 border-slate-700 hover:border-slate-500'}`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <Icon className="w-5 h-5 text-sky-300 shrink-0" aria-hidden="true" />
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-100 whitespace-nowrap">{d.tag}</span>
                  </div>
                  <h3 className="font-semibold text-white">{d.title}</h3>
                  <p className="text-sm text-slate-300 mt-1">{d.blurb}</p>
                </button>
              );
            })}
          </div>
          <p className="text-sm text-slate-400">Examples use sample receipts and photo descriptions, labelled as sample data.</p>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* On small screens an example's answer comes before its case details; the form always comes first. */}
          <div className={`lg:col-span-5 space-y-6 min-w-0 ${mode.kind === 'demo' ? 'order-2 lg:order-1' : ''}`}>
            {mode.kind === 'own' && (
              <CheckForm busy={loading} onSubmit={(c) => { moveFocus.current = true; setMode({ kind: 'own', case: c }); evaluate(c); }} />
            )}
            {activeCase && <EvidencePanel c={activeCase} />}
          </div>

          <div className={`lg:col-span-7 space-y-6 min-w-0 ${mode.kind === 'demo' ? 'order-1 lg:order-2' : ''}`} aria-live="polite" aria-busy={loading}>
            {error ? (
              <div role="alert" className="bg-slate-900/80 border border-amber-400/50 rounded-2xl p-6 space-y-2">
                <p className="flex items-center gap-2 text-amber-200 font-semibold">
                  <AlertTriangle className="w-5 h-5" aria-hidden="true" /> Something went wrong
                </p>
                <p className="text-slate-200">{error}</p>
                <p className="text-sm text-slate-300">No result is shown, because RemedyAI only reports what its engine actually determined.</p>
              </div>
            ) : loading ? (
              <div className="bg-slate-900/70 border border-slate-700 rounded-2xl p-12 text-center">
                <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" aria-hidden="true"></div>
                <p className="text-slate-200 mt-3">Checking the official sources...</p>
              </div>
            ) : evaluation && activeCase ? (
              <Result
                evaluation={evaluation}
                c={activeCase}
                verdictRef={verdictRef}
                onConfirm={mode.kind === 'own' ? confirmCheck : undefined}
                onDownload={downloadPdf}
                downloading={downloading}
              />
            ) : mode.kind === 'own' ? (
              <div className="bg-slate-900/50 border border-dashed border-slate-600 rounded-2xl p-8 text-slate-300">
                Your options will appear here after you fill in the form.
              </div>
            ) : null}
          </div>
        </div>

        <SourceWatchPanel data={sources} />
        <PrivacySection />
      </main>

      <footer className="border-t border-slate-800 py-8 px-4 text-sm text-slate-300">
        <div className="max-w-4xl mx-auto space-y-2 text-center">
          <p>
            <b className="text-slate-100">Not legal advice.</b> RemedyAI helps you prepare a claim. It does not guarantee a repair,
            replacement or refund; the maker, card issuer or store makes the final decision.
          </p>
          <p>
            RemedyAI is not affiliated with or endorsed by Apple, Visa, Sony, Samsung, Best Buy, Currys or any retailer named.
            Names are used only to identify products and programs.
          </p>
          <p>
            Contains public sector information licensed under the{' '}
            <a className="underline" href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>.
          </p>
          <p className="text-slate-400">
            Built for AWS Zero to Shipped on AWS Lambda, Amazon Textract, Amazon Bedrock, DynamoDB, S3 and CloudFront ·{' '}
            <a href="#privacy" className="underline">Privacy</a> · <a href={REPO_URL} className="underline">Source code</a>
          </p>
        </div>
      </footer>
    </div>
  );
}

function Result({
  evaluation, c, verdictRef, onConfirm, onDownload, downloading,
}: {
  evaluation: RemedyEvaluation;
  c: NormalizedCase;
  verdictRef: RefObject<HTMLHeadingElement | null>;
  onConfirm?: (id: string) => void;
  onDownload: () => void;
  downloading: boolean;
}) {
  const invalid = evaluation.unmatched_reason?.startsWith('INVALID INPUT');
  const routes = evaluation.matched_routes;
  const has = evaluation.has_coverage && routes.length > 0;
  const hold = !evaluation.pdf_allowed;

  const headline = invalid
    ? 'Please check the dates'
    : !has
      ? "We couldn't find a verified option"
      : hold
        ? 'Confirm one detail first'
        : verdictFor(routes[0]);

  return (
    <>
      <section
        aria-labelledby="verdict"
        className={`rounded-2xl p-5 sm:p-6 space-y-2 border ${!has ? 'bg-rose-500/10 border-rose-400/40' : hold ? 'bg-amber-500/10 border-amber-400/50' : 'bg-emerald-500/10 border-emerald-400/40'}`}
      >
        <p className="text-sm text-slate-300">Your answer</p>
        <h2 id="verdict" ref={verdictRef} tabIndex={-1} className="text-2xl font-bold text-white flex items-start gap-2 focus:outline-none">
          {has && !hold ? <CheckCircle2 className="w-7 h-7 text-emerald-300 shrink-0 mt-0.5" aria-hidden="true" /> : <ShieldAlert className={`w-7 h-7 shrink-0 mt-0.5 ${hold ? 'text-amber-300' : 'text-rose-300'}`} aria-hidden="true" />}
          {headline}
        </h2>
        {has && routes.length > 1 && <p className="text-slate-200">{routes.length} options found. The details of each are below.</p>}
        {has && !hold && <p className="text-slate-200">Start with "What to do next" below.</p>}
        {!has && <p className="text-slate-200">{invalid ? evaluation.unmatched_reason?.replace('INVALID INPUT: ', '') : 'None of the official sources RemedyAI checks covers this case. That does not mean nothing does.'}</p>}
      </section>

      <Checks checks={evaluation.checks} onConfirm={onConfirm} />
      {evaluation.timeline && <Timeline evaluation={evaluation} />}

      {has ? (
        <>
          {routes.map((r, i) => (
            <RouteCard key={r.route_id} route={r} index={i + 1} c={c} onDownload={onDownload} downloading={downloading} pdfAllowed={evaluation.pdf_allowed} />
          ))}
          <Notes notes={evaluation.notes} />
        </>
      ) : (
        <div className="bg-slate-900/80 border border-slate-700 rounded-2xl p-5 sm:p-6 space-y-4">
          <Notes notes={evaluation.notes} />
          <div>
            <h3 className="font-semibold text-slate-100 mb-2">What you can still try</h3>
            <ul className="space-y-2">
              {evaluation.next_steps.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-slate-200">
                  <ArrowRight className="w-4 h-4 text-rose-300 shrink-0 mt-1" aria-hidden="true" /> {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  );
}

function Checks({ checks, onConfirm }: { checks: CaseCheck[]; onConfirm?: (id: string) => void }) {
  if (!checks.length) return null;
  return (
    <section aria-labelledby="checks-heading" className="bg-slate-900/80 border border-amber-400/40 rounded-2xl p-5 space-y-3">
      <h3 id="checks-heading" className="font-semibold text-amber-100 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5" aria-hidden="true" /> Checked against your receipt
      </h3>
      <ul className="space-y-3">
        {checks.map((ch) => (
          <li key={ch.id} className="space-y-2">
            <p className="text-slate-100">
              <span className={`text-xs font-bold uppercase tracking-wide mr-2 ${ch.confirmed ? 'text-emerald-300' : ch.severity === 'hard' ? 'text-amber-300' : 'text-slate-300'}`}>
                {ch.confirmed ? 'Confirmed' : ch.severity === 'hard' ? 'Needs confirmation' : 'Please check'}
              </span>
              {ch.message}
            </p>
            {ch.severity === 'hard' && !ch.confirmed && ch.confirm_label && onConfirm && (
              <label className="flex items-center gap-3 text-slate-100 min-h-11">
                <input type="checkbox" className="w-5 h-5" onChange={(e) => e.target.checked && onConfirm(ch.id)} />
                {ch.confirm_label}
              </label>
            )}
            {ch.severity === 'hard' && !ch.confirmed && !onConfirm && (
              <p className="text-sm text-slate-300">If this is wrong, go back and change the country.</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Timeline({ evaluation }: { evaluation: RemedyEvaluation }) {
  const tl = evaluation.timeline!;
  const rows: [string, string][] = [
    ['Bought', humanDate(tl.purchase_date)],
    ['Broke', `${humanDate(tl.failure_date)} (${tl.months_before_failure} months after purchase)`],
    ['Claim date', humanDate(tl.claim_date)],
    ...evaluation.matched_routes
      .filter((r) => r.deadline)
      .map((r): [string, string] => [r.deadline_label ?? 'Deadline', `${humanDate(r.deadline)}${r.days_left != null ? ` (${daysLeftText(r.days_left)})` : ''}`]),
  ];
  return (
    <section aria-labelledby="timeline-heading" className="bg-slate-900/80 border border-slate-700 rounded-2xl p-5 space-y-3">
      <h3 id="timeline-heading" className="font-semibold text-slate-100 flex items-center gap-2">
        <CalendarDays className="w-5 h-5 text-sky-300" aria-hidden="true" /> Timeline
      </h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-slate-300">{k}</dt>
            <dd className="text-slate-50 font-medium">{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <section className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4 space-y-2">
      <h3 className="font-semibold text-slate-100">Sources checked that did not apply</h3>
      <ul className="space-y-2">
        {notes.map((n, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-200">
            <Info className="w-4 h-4 text-sky-300 shrink-0 mt-0.5" aria-hidden="true" /> {n}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PrivacySection() {
  return (
    <section id="privacy" aria-labelledby="privacy-heading" className="bg-slate-900/70 border border-slate-700 rounded-2xl p-5 sm:p-6 space-y-3 scroll-mt-24">
      <h2 id="privacy-heading" className="font-bold text-white text-lg flex items-center gap-2">
        <Lock className="w-5 h-5 text-sky-300" aria-hidden="true" /> Privacy
      </h2>
      <div className="grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm text-slate-200 leading-relaxed">
        <p>
          <b className="text-slate-50">What we use.</b> The details you type (product, dates, store, how you paid, the fault)
          and, only if you choose, a receipt photo and a photo of the fault. We use them only to check your options and
          prepare your claim, because you asked us to.
        </p>
        <p>
          <b className="text-slate-50">What we keep.</b> Nothing. RemedyAI does not save your details or photos. There are no
          accounts, cookies, analytics or ads. Error logs record only the type of error and are deleted after 14 days.
        </p>
        <p>
          <b className="text-slate-50">Who processes photos.</b> Amazon Web Services, in the US East (N. Virginia) region.
          Receipts are read by Amazon Textract and fault photos by Amazon Bedrock. AWS says Bedrock does not store your
          photo or use it to train models.{' '}
          {TEXTRACT_OPTED_OUT
            ? 'This service is opted out of AWS using Textract content to improve its services.'
            : 'Amazon Textract may keep content to improve its service unless the account owner opts out. If that matters to you, skip the receipt photo and type the details in instead.'}
        </p>
        <p>
          <b className="text-slate-50">Before you upload.</b> Cover your name, address, card number and any faces. Photos are
          re-saved in your browser before upload, which removes location (GPS) data. Nothing is sent until you press "Read
          photos".
        </p>
        <p>
          <b className="text-slate-50">Daily limit.</b> To keep the free photo reading fair, we count photo reads per visitor
          using a one-way code made from your IP address with a key that changes every day. The code and the key are deleted
          after 2 days; your IP address itself is never stored.
        </p>
        <p>
          <b className="text-slate-50">Questions.</b> Open an issue on the{' '}
          <a href={`${REPO_URL}/issues`} className="underline text-sky-300">project's GitHub page</a> and ask to be contacted.
          Please don't post personal details there.
        </p>
      </div>
    </section>
  );
}

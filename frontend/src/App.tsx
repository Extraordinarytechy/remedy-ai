import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import {
  AlertTriangle, ArrowRight, BadgeCheck, CalendarDays, CheckCircle2, ClipboardCheck, Coffee, CreditCard, Eye, FileText, Info,
  Lock, RefreshCw, Search, ShieldAlert, ShieldCheck, Smartphone, Tv,
} from 'lucide-react';
import { api } from './api';
import type { CaseCheck, NormalizedCase, RemedyEvaluation, SourcesResponse } from './types';
import { EvidencePanel } from './components/EvidencePanel';
import { RouteCard } from './components/RouteCard';
import { SourcesTable, sourcesSummary } from './components/SourceWatchPanel';
import { CheckForm } from './components/CheckForm';
import { CoveragePanel } from './components/CoveragePanel';
import { Disclosure, Modal, ThemeToggle } from './components/ui';
import { STATUS_LABEL, TONE_CLASSES, daysLeftText, humanDate, isActionable, shortDate, verdictFor } from './components/labels';

const REPO_URL = 'https://github.com/Extraordinarytechy/remedy-ai';

// Set to true once the AWS account has an AI services opt-out policy for Amazon Textract.
const TEXTRACT_OPTED_OUT = true; // AWS Organizations AI services opt-out policy attached 2026-10-01

const DEMOS = [
  { key: 'case1_apple_iphone14plus', icon: Smartphone, tag: 'Free repair program', title: 'iPhone 14 Plus camera' },
  { key: 'case2_visa_infinite_sony', icon: CreditCard, tag: 'Card benefit', title: 'Headphones, Visa Infinite' },
  { key: 'case3_uk_samsung_tv', icon: Tv, tag: 'Consumer law', title: 'TV bought in the UK' },
  { key: 'case4_unknown_unsupported', icon: Coffee, tag: 'No match', title: 'Espresso machine' },
] as const;

type Mode = { kind: 'demo'; key: string } | { kind: 'own'; case: NormalizedCase | null };
type Dialog = 'privacy' | 'sources' | null;

export default function App() {
  const [fixtures, setFixtures] = useState<Record<string, NormalizedCase> | null>(null);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [heroEval, setHeroEval] = useState<RemedyEvaluation | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: 'demo', key: DEMOS[0].key });
  const [evaluation, setEvaluation] = useState<RemedyEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const verdictRef = useRef<HTMLHeadingElement>(null);
  const moveFocus = useRef(false);

  const activeCase: NormalizedCase | null = mode.kind === 'demo' ? (fixtures?.[mode.key] ?? null) : mode.case;

  useEffect(() => {
    api.fixtures()
      .then((fx) => {
        setFixtures(fx);
        api.evaluate(fx[DEMOS[0].key]).then(setHeroEval).catch(() => setHeroEval(null));
      })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
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

  useEffect(() => {
    if (evaluation && moveFocus.current) {
      verdictRef.current?.focus();
      moveFocus.current = false;
    }
  }, [evaluation]);

  const goToTry = () => document.getElementById('try')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const startOwn = () => {
    setMode({ kind: 'own', case: null });
    setEvaluation(null);
    setError(null);
    setLoading(false);
    setTimeout(goToTry, 0);
  };
  const showDemo = (key: string) => {
    moveFocus.current = false;
    setMode({ kind: 'demo', key });
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
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  const summary = sourcesSummary(sources);

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-full focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-ink">
        Skip to content
      </a>

      <header className="sticky top-0 z-50 border-b border-line bg-canvas/80 backdrop-blur-lg">
        <div className="container-page flex h-16 items-center justify-between gap-4">
          <a href="#main" className="flex items-center gap-2.5" aria-label="RemedyAI home">
            <span className="inline-flex size-8 items-center justify-center rounded-xl bg-accent text-accent-ink" aria-hidden="true">
              <ShieldCheck className="size-[18px]" />
            </span>
            <span className="text-[17px] font-semibold tracking-tight">RemedyAI</span>
          </a>
          <nav className="hidden items-center gap-7 text-sm font-medium text-muted md:flex" aria-label="Sections">
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#coverage" className="hover:text-ink">Coverage</a>
            <a href="#try" className="hover:text-ink">Try it</a>
            <a href="#faq" className="hover:text-ink">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button onClick={startOwn} className="btn-primary hidden min-h-10 px-4 text-sm sm:inline-flex">Check my product</button>
          </div>
        </div>
      </header>

      <main id="main" className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div aria-hidden="true" className="pointer-events-none absolute -right-40 -top-40 size-[640px] rounded-full bg-[radial-gradient(closest-side,var(--c-accent-soft),transparent)] opacity-90" />
          <div className="container-page relative grid items-center gap-12 py-16 sm:py-24 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-7">
              <p className="eyebrow">After the warranty ends</p>
              <h1 className="text-4xl font-semibold leading-[1.05] tracking-tight text-balance sm:text-6xl">
                Your warranty ended. You may still get a free repair.
              </h1>
              <p className="max-w-xl text-lg leading-relaxed text-muted text-pretty">
                RemedyAI checks a broken product against official sources: repair programs, warranties, card benefits and
                consumer law. You get the next step, the deadline and a claim ready to send.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button onClick={startOwn} className="btn-primary min-h-12 px-6 text-base">
                  <Search className="size-5" aria-hidden="true" /> Check my product
                </button>
                <button onClick={goToTry} className="btn-secondary min-h-12 px-6 text-base">See an example</button>
              </div>
              <ul className="flex flex-wrap gap-2" aria-label="Why you can trust it">
                <li className="chip"><BadgeCheck className="size-3.5 text-accent-text" aria-hidden="true" /> Official sources only</li>
                <li className="chip"><Lock className="size-3.5 text-accent-text" aria-hidden="true" /> No sign-up, nothing stored</li>
                <li className="chip"><RefreshCw className="size-3.5 text-accent-text" aria-hidden="true" /> Sources re-checked daily</li>
              </ul>
            </div>
            <HeroPreview evaluation={heroEval} onOpen={goToTry} />
          </div>
        </section>

        {/* How it works */}
        <section id="how" aria-labelledby="how-heading" className="scroll-mt-20 border-y border-line bg-surface">
          <div className="container-page py-16 sm:py-20">
            <p className="eyebrow">How it works</p>
            <h2 id="how-heading" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Three steps, about two minutes</h2>
            <ol className="mt-10 grid gap-6 md:grid-cols-3">
              {[
                { icon: FileText, title: 'Describe the problem', text: 'The product, when you bought it, when it broke and what went wrong. Photos are optional.' },
                { icon: ClipboardCheck, title: 'We check official sources', text: 'Repair programs, warranties, card benefits and consumer law, each from its official page.' },
                { icon: CheckCircle2, title: 'Get your next step', text: "What to do, the deadline, what you'll need, and a claim PDF." },
              ].map((s, i) => (
                <li key={s.title} className="relative rounded-3xl border border-line bg-canvas p-6">
                  <span className="absolute right-6 top-6 text-sm font-semibold text-faint">0{i + 1}</span>
                  <span className="inline-flex size-11 items-center justify-center rounded-2xl bg-accent-soft text-accent-text">
                    <s.icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-5 text-lg font-semibold">{s.title}</h3>
                  <p className="mt-1.5 text-muted">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="container-page py-16 sm:py-24">
          <CoveragePanel />
        </div>

        {/* Try it */}
        <section id="try" aria-labelledby="try-heading" className="scroll-mt-20 border-t border-line bg-surface">
          <div className="container-page space-y-8 py-16 sm:py-24">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="space-y-3">
                <p className="eyebrow">Try it</p>
                <h2 id="try-heading" className="text-3xl font-semibold tracking-tight sm:text-4xl">See an answer, or check your own</h2>
              </div>
              <button onClick={startOwn} className={mode.kind === 'own' ? 'btn-primary' : 'btn-secondary'} aria-pressed={mode.kind === 'own'}>
                <Search className="size-4" aria-hidden="true" /> Your product
              </button>
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Examples">
              {DEMOS.map((d) => {
                const selected = mode.kind === 'demo' && mode.key === d.key;
                return (
                  <button
                    key={d.key}
                    onClick={() => showDemo(d.key)}
                    aria-pressed={selected}
                    className={`flex shrink-0 items-center gap-2.5 rounded-full border px-4 py-2.5 text-sm font-medium transition-colors ${selected ? 'border-accent bg-accent-soft text-accent-text' : 'border-line bg-canvas text-muted hover:text-ink'}`}
                  >
                    <d.icon className="size-4" aria-hidden="true" />
                    <span className="text-ink">{d.title}</span>
                    <span className="hidden text-xs text-faint sm:inline">· {d.tag}</span>
                  </button>
                );
              })}
            </div>
            {mode.kind === 'demo' && <p className="-mt-4 text-sm text-faint">Examples use sample receipts and photo descriptions, labelled "Sample data".</p>}

            <div className="grid gap-8 lg:grid-cols-12">
              {/* On small screens an example's answer comes before its case details; the form always comes first. */}
              <div className={`min-w-0 space-y-6 lg:col-span-5 ${mode.kind === 'demo' ? 'order-2 lg:order-1' : ''}`}>
                {mode.kind === 'own' && (
                  <CheckForm
                    busy={loading}
                    onOpenPrivacy={() => setDialog('privacy')}
                    onSubmit={(c) => { moveFocus.current = true; setMode({ kind: 'own', case: c }); evaluate(c); }}
                  />
                )}
                {activeCase && <EvidencePanel c={activeCase} />}
              </div>

              <div className={`min-w-0 space-y-5 lg:col-span-7 ${mode.kind === 'demo' ? 'order-1 lg:order-2' : ''}`} aria-live="polite" aria-busy={loading}>
                {error ? (
                  <div role="alert" className="card space-y-2 border-warn-line bg-warn-soft p-6 text-warn-ink">
                    <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="size-5" aria-hidden="true" /> Something went wrong</p>
                    <p>{error}</p>
                    <p className="text-sm">No result is shown, because RemedyAI only reports what its engine actually determined.</p>
                  </div>
                ) : loading ? (
                  <div className="card space-y-4 p-6" aria-label="Checking the official sources">
                    <div className="h-4 w-24 animate-pulse rounded-full bg-subtle" />
                    <div className="h-7 w-3/4 animate-pulse rounded-full bg-subtle" />
                    <div className="h-4 w-1/2 animate-pulse rounded-full bg-subtle" />
                    <p className="pt-2 text-sm text-faint">Checking the official sources...</p>
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
                  <div className="flex min-h-48 items-center justify-center rounded-3xl border border-dashed border-line-strong p-8 text-center text-muted">
                    Your answer will appear here.
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        {/* Trust */}
        <section aria-labelledby="trust-heading" className="container-page py-16 sm:py-24">
          <div className="space-y-10">
            <div className="max-w-2xl space-y-3">
              <p className="eyebrow">Why you can rely on it</p>
              <h2 id="trust-heading" className="text-3xl font-semibold tracking-tight sm:text-4xl">Answers come from sources, not guesses</h2>
              {summary && (
                <p className="text-muted">
                  {summary.count} official sources, last checked automatically on {shortDate(summary.last)}
                  {summary.issues > 0 ? ` · ${summary.issues} need attention` : ''}.{' '}
                  <button onClick={() => setDialog('sources')} className="link">View source status</button>
                </p>
              )}
            </div>
            <ul className="grid gap-4 md:grid-cols-3">
              {[
                { icon: BadgeCheck, title: 'Official sources only', text: 'Every option is tied to an official page, verified before it goes live. No source, no answer.' },
                { icon: RefreshCw, title: 'Re-checked every day', text: 'If a page changes or a program ends, the option is marked "check it first" and left out of the claim letter.' },
                { icon: Eye, title: 'AI reads, never decides', text: "AI reads your receipt and photo, and you see what it read. Fixed rules from the source decide whether you're covered." },
              ].map((t) => (
                <li key={t.title} className="card p-6">
                  <t.icon className="size-5 text-accent-text" aria-hidden="true" />
                  <h3 className="mt-3 font-semibold">{t.title}</h3>
                  <p className="mt-1 text-sm text-muted">{t.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" aria-labelledby="faq-heading" className="scroll-mt-20 border-t border-line bg-surface">
          <div className="container-page grid gap-10 py-16 sm:py-24 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="space-y-3">
              <p className="eyebrow">FAQ</p>
              <h2 id="faq-heading" className="text-3xl font-semibold tracking-tight sm:text-4xl">Questions, answered</h2>
            </div>
            <div className="space-y-2.5">
              <Faq q="Is it free? Do I need an account?">Yes, it's free, and there's no sign-up. A check takes about two minutes.</Faq>
              <Faq q="What do you keep about me?">
                Nothing. RemedyAI doesn't save your details or photos, and uses no cookies, analytics or ads. Photos are optional.{' '}
                <button onClick={() => setDialog('privacy')} className="link">Read the privacy notice</button>
              </Faq>
              <Faq q="Which products and countries work?">
                Any brand, including TVs and home appliances, if you bought it from a UK store or paid with a Visa Infinite card
                in the U.S. Apple products also get Apple's repair programs and, in the U.S., Apple's one-year warranty. Google
                Pixel devices get Google's repair programs and, if bought in the U.S. or Canada, Google's one-year warranty.{' '}
                <a href="#coverage" className="link">See full coverage</a>
              </Faq>
              <Faq q="Is this legal advice?">
                No. RemedyAI helps you prepare a claim based on what official sources say. The maker, card issuer or store makes
                the final decision.
              </Faq>
              <Faq q="How do you keep sources up to date?">
                Every source page is re-read automatically each day. If a page disappears, its key wording changes or Apple drops a
                program, the option is marked "check it first" until it has been verified again.{' '}
                <button onClick={() => setDialog('sources')} className="link">View source status</button>
              </Faq>
              <Faq q="What if my product isn't covered?">
                RemedyAI tells you so instead of guessing, and suggests what you can still try. New sources are added once their
                official page has been verified.
              </Faq>
            </div>
          </div>
        </section>

        {/* Closing call to action */}
        <section className="container-page py-16 sm:py-24">
          <div className="relative overflow-hidden rounded-[2rem] bg-accent px-8 py-14 text-accent-ink sm:px-14">
            <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-white/10" />
            <h2 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">Before you pay for a repair, check what you may still be owed.</h2>
            <p className="mt-3 max-w-xl text-lg opacity-90">About two minutes. No sign-up.</p>
            <button onClick={startOwn} className="mt-8 inline-flex min-h-12 items-center gap-2 rounded-full bg-accent-ink px-6 font-semibold text-accent hover:opacity-90">
              Check my product <ArrowRight className="size-4" aria-hidden="true" />
            </button>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="container-page flex flex-col gap-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 font-medium text-ink">
            <ShieldCheck className="size-4 text-accent-text" aria-hidden="true" /> RemedyAI
          </p>
          <nav className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Footer">
            <button onClick={() => setDialog('privacy')} className="hover:text-ink">Privacy</button>
            <button onClick={() => setDialog('sources')} className="hover:text-ink">Sources</button>
            <a href={REPO_URL} className="hover:text-ink">GitHub</a>
          </nav>
        </div>
        <div className="container-page border-t border-line py-5 text-xs leading-relaxed text-faint">
          Not legal advice. RemedyAI is not affiliated with or endorsed by Apple, Visa, Sony, Samsung, Best Buy, Currys or any other
          company named; names are used only to identify products and programs. Contains public sector information licensed under
          the <a className="underline" href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>.
        </div>
      </footer>

      <Modal open={dialog === 'privacy'} onClose={() => setDialog(null)} title="Privacy">
        <PrivacyNotice />
      </Modal>
      <Modal open={dialog === 'sources'} onClose={() => setDialog(null)} title="Source status" wide>
        {sources ? <SourcesTable data={sources} /> : <p className="text-muted">Source status is not available right now.</p>}
      </Modal>
    </div>
  );
}

function Faq({ q, children }: { q: string; children: ReactNode }) {
  return <Disclosure title={q}>{children}</Disclosure>;
}

/** A real engine result for the first example, shown in the hero. */
function HeroPreview({ evaluation, onOpen }: { evaluation: RemedyEvaluation | null; onOpen: () => void }) {
  const route = evaluation?.matched_routes[0];
  return (
    <div className="relative">
      <div className="card p-6 shadow-[0_24px_60px_-24px_rgb(0_0_0/0.25)] sm:p-7">
        <div className="flex items-center justify-between gap-3">
          <span className="chip"><Smartphone className="size-3.5" aria-hidden="true" /> Example · iPhone 14 Plus</span>
          <span className="text-xs text-faint">Sample data</span>
        </div>
        {route ? (
          <>
            <p className="mt-6 text-sm font-medium text-faint">Your answer</p>
            <p className="mt-1 text-2xl font-semibold leading-snug tracking-tight">{verdictFor(route)}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_CLASSES[STATUS_LABEL[route.status].tone]}`}>
                {STATUS_LABEL[route.status].text}
              </span>
              <span className="rounded-full bg-subtle px-2.5 py-0.5 text-xs font-medium text-muted">{route.provider.replace(' Inc.', '')} service program</span>
            </div>
            {route.deadline && (
              <div className="mt-6 flex items-center gap-3 rounded-2xl bg-accent-soft px-4 py-3 text-sm">
                <CalendarDays className="size-5 text-accent-text" aria-hidden="true" />
                <span><b>Free repair ends {humanDate(route.deadline)}</b> <span className="text-muted">· {daysLeftText(route.days_left)}</span></span>
              </div>
            )}
            <button onClick={onOpen} className="btn-ghost mt-5 -ml-3">See the full answer <ArrowRight className="size-4" aria-hidden="true" /></button>
          </>
        ) : (
          <div className="mt-6 space-y-3" aria-hidden="true">
            <div className="h-4 w-24 animate-pulse rounded-full bg-subtle" />
            <div className="h-7 w-5/6 animate-pulse rounded-full bg-subtle" />
            <div className="h-12 w-full animate-pulse rounded-2xl bg-subtle" />
          </div>
        )}
      </div>
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
  // A hard receipt check waiting for the user, or no option they can act on yet.
  const pendingCheck = evaluation.checks.some((ch) => ch.severity === 'hard' && !ch.confirmed);
  const top = routes.find(isActionable) ?? routes[0];
  const hold = !evaluation.pdf_allowed || !routes.some(isActionable);
  const headline = invalid
    ? 'Please check the dates'
    : !has
      ? "We couldn't find a verified option"
      : pendingCheck
        ? 'Confirm one detail first'
        : verdictFor(top);
  const tone = !has ? 'border-bad-soft bg-bad-soft' : hold ? 'border-warn-line bg-warn-soft' : 'border-transparent bg-good-soft';

  return (
    <>
      <section aria-labelledby="verdict" className={`rounded-3xl border p-6 sm:p-7 ${tone}`}>
        <p className="text-sm font-medium text-muted">Your answer</p>
        <h3 id="verdict" ref={verdictRef} tabIndex={-1} className="mt-1.5 flex items-start gap-2.5 text-2xl font-semibold leading-snug tracking-tight focus:outline-none">
          {has && !hold
            ? <CheckCircle2 className="mt-1 size-6 shrink-0 text-good-ink" aria-hidden="true" />
            : <ShieldAlert className={`mt-1 size-6 shrink-0 ${hold ? 'text-warn-ink' : 'text-bad-ink'}`} aria-hidden="true" />}
          {headline}
        </h3>
        <p className="mt-2 text-muted">
          {invalid
            ? evaluation.unmatched_reason?.replace('INVALID INPUT: ', '')
            : !has
              ? "None of the official sources RemedyAI checks covers this case. Other help may still exist; see what you can try below."
              : routes.length > 1
                ? `${routes.length} options found. Start with "What to do next".`
                : 'Start with "What to do next" below.'}
        </p>
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
        <div className="card space-y-4 p-6">
          <h4 className="font-semibold">What you can still try</h4>
          <ul className="space-y-2">
            {evaluation.next_steps.map((s, i) => (
              <li key={i} className="flex items-start gap-2.5 text-muted">
                <ArrowRight className="mt-1 size-4 shrink-0 text-accent-text" aria-hidden="true" /> {s}
              </li>
            ))}
          </ul>
          <Notes notes={evaluation.notes} />
        </div>
      )}
    </>
  );
}

function Checks({ checks, onConfirm }: { checks: CaseCheck[]; onConfirm?: (id: string) => void }) {
  if (!checks.length) return null;
  return (
    <section aria-labelledby="checks-heading" className="space-y-3 rounded-3xl border border-warn-line bg-warn-soft p-5 text-warn-ink">
      <h4 id="checks-heading" className="flex items-center gap-2 font-semibold"><AlertTriangle className="size-5" aria-hidden="true" /> Checked against your receipt</h4>
      <ul className="space-y-3">
        {checks.map((ch) => (
          <li key={ch.id} className="space-y-2">
            <p>
              <span className="mr-2 text-xs font-bold uppercase tracking-wide">
                {ch.confirmed ? 'Confirmed' : ch.severity === 'hard' ? 'Needs confirmation' : 'Please check'}
              </span>
              {ch.message}
            </p>
            {ch.severity === 'hard' && !ch.confirmed && ch.confirm_label && onConfirm && (
              <label className="flex min-h-11 items-center gap-3 font-medium">
                <input type="checkbox" className="size-5 accent-[var(--c-accent)]" onChange={(e) => e.target.checked && onConfirm(ch.id)} />
                {ch.confirm_label}
              </label>
            )}
            {ch.severity === 'hard' && !ch.confirmed && !onConfirm && <p className="text-sm">If this is wrong, go back and change the country.</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Timeline({ evaluation }: { evaluation: RemedyEvaluation }) {
  const tl = evaluation.timeline!;
  const stops: { label: string; date: string; note?: string; strong?: boolean }[] = [
    { label: 'Bought', date: tl.purchase_date },
    { label: 'Broke', date: tl.failure_date, note: `${tl.months_before_failure} months later` },
    { label: 'Claim date', date: tl.claim_date, note: 'today' },
    ...evaluation.matched_routes
      .filter((r) => r.deadline)
      .map((r) => ({ label: r.deadline_label ?? 'Deadline', date: r.deadline!, note: daysLeftText(r.days_left), strong: true })),
  ];
  return (
    <section aria-labelledby="timeline-heading" className="card p-6">
      <h4 id="timeline-heading" className="flex items-center gap-2 font-semibold"><CalendarDays className="size-5 text-accent-text" aria-hidden="true" /> Timeline</h4>
      <ol className="mt-5 grid grid-cols-2 gap-3">
        {stops.map((s) => (
          <li key={`${s.label}-${s.date}`} className={`relative rounded-2xl border px-4 py-3 ${s.strong ? 'border-accent bg-accent-soft' : 'border-line'}`}>
            <p className="text-xs font-medium uppercase tracking-wide text-faint">{s.label}</p>
            <p className="mt-1 whitespace-nowrap font-semibold">{humanDate(s.date)}</p>
            {s.note && <p className="text-sm text-muted">{s.note}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <Disclosure title={<><Info className="size-4 text-accent-text" aria-hidden="true" /> Sources checked that did not apply</>} meta={`${notes.length}`}>
      <ul className="space-y-2">
        {notes.map((n, i) => <li key={i}>{n}</li>)}
      </ul>
    </Disclosure>
  );
}

function PrivacyNotice() {
  const rows: [string, ReactNode][] = [
    ['What we use', 'The details you type (product, dates, store, how you paid, the fault) and, only if you choose, a receipt photo and a photo of the fault. We use them only to check your options and prepare your claim, because you asked us to.'],
    ['What we keep', 'Nothing. RemedyAI does not save your details or photos. There are no accounts, cookies, analytics or ads. Your browser remembers only your light/dark choice. Error logs record only the type of error and are deleted after 14 days.'],
    ['Who processes photos', <>Amazon Web Services, in the US East (N. Virginia) region. Receipts are read by Amazon Textract and fault photos by Amazon Bedrock. AWS says Bedrock does not store your photo or use it to train models.{' '}
      {TEXTRACT_OPTED_OUT
        ? "RemedyAI's AWS account is opted out of AWS using this content to improve its AI services, including Textract."
        : 'Amazon Textract may keep content to improve its service unless the account owner opts out. If that matters to you, skip the receipt photo and type the details in instead.'}</>],
    ['Before you upload', 'Cover your name, address, card number and any faces. Photos are re-saved in your browser before upload, which removes location (GPS) data. Nothing is sent until you press "Read photos".'],
    ['Daily limit', "To keep free photo reading fair, photo reads are counted per visitor using a one-way code made from your IP address with a key that changes every day. The code and the key expire 2 days after they were last used and are then removed automatically; your IP address itself is never stored. Claim PDFs are counted the same way."],
    ['Questions', <>Open an issue on the <a href={`${REPO_URL}/issues`} className="link">project's GitHub page</a> and ask to be contacted. Please don't post personal details there.</>],
  ];
  return (
    <dl className="space-y-4">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt className="font-semibold">{k}</dt>
          <dd className="mt-1 leading-relaxed text-muted">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

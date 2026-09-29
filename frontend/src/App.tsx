import { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  FileText,
  Download,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Info,
  Sparkles,
  Copy,
  Check,
  CreditCard,
  Smartphone,
  Cpu,
  Tv,
  Coffee,
  ChevronRight,
  ArrowRight
} from 'lucide-react';

interface ReceiptData {
  store_name?: string;
  purchase_date?: string;
  item_description?: string;
  total_amount?: number;
  currency?: string;
  payment_type?: string;
  confidence_score: number;
}

interface VisualDefectEvidence {
  anomaly_detected: boolean;
  visible_physical_damage: boolean;
  physical_damage_severity: 'none' | 'cosmetic' | 'screen_cracked' | 'severe';
  symptom_category?: string;
  visual_observations: string[];
  confidence_score: number;
  disclaimer?: string;
}

interface NormalizedCase {
  case_id: string;
  product_name: string;
  product_brand?: string;
  product_model?: string;
  purchase_date: string;
  failure_date: string;
  purchase_country: string;
  retailer?: string;
  payment_method?: string;
  original_warranty_years: number;
  defect_description: string;
  evaluation_date?: string;
  already_paid_for_repair?: boolean;
  receipt_data?: ReceiptData;
  visual_evidence?: VisualDefectEvidence;
}

interface ProvenanceChain {
  claim: string;
  why_matched: string;
  evidence: string[];
  source_citation: string;
  source_url: string;
  conditions: string[];
  exceptions: string[];
}

interface MatchedRoute {
  route_id: string;
  route_type: 'manufacturer_service_program' | 'card_benefit' | 'statutory_consumer_law';
  title: string;
  provider: string;
  status:
    | 'POTENTIALLY_ELIGIBLE'
    | 'ELIGIBLE_PENDING_INSPECTION'
    | 'PENDING_SERIAL_VERIFICATION'
    | 'OUTSIDE_WINDOW'
    | 'INSUFFICIENT_EVIDENCE';
  summary: string;
  primary_source: {
    title: string;
    url: string;
    verified_at: string;
  };
  provenance: ProvenanceChain;
  recommended_action: string;
  confidence_score: number;
}

interface RemedyEvaluation {
  case_id: string;
  evaluated_at: string;
  evaluation_date?: string;
  has_coverage: boolean;
  matched_routes: MatchedRoute[];
  unmatched_reason?: string;
  notes?: string[];
  next_steps: string[];
  disclaimer: string;
}

// Base URL of the deployed API (e.g. the API Gateway URL). Empty = same origin,
// which works with the Vite dev proxy or an Amplify rewrite for /api/*.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

const DEFAULT_CASE_KEY = 'case1_apple_iphone14plus';

async function readJson<T>(res: Response): Promise<T> {
  const type = res.headers.get('content-type') ?? '';
  if (!res.ok || !type.includes('application/json')) {
    throw new Error(`API returned ${res.status} (${type || 'no content type'})`);
  }
  return (await res.json()) as T;
}

export default function App() {
  const [fixtures, setFixtures] = useState<Record<string, NormalizedCase> | null>(null);
  const [selectedCaseKey, setSelectedCaseKey] = useState<string>(DEFAULT_CASE_KEY);
  const [evaluation, setEvaluation] = useState<RemedyEvaluation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [pdfDownloading, setPdfDownloading] = useState<boolean>(false);
  const [copiedLetter, setCopiedLetter] = useState<boolean>(false);

  const activeCase: NormalizedCase | null = fixtures?.[selectedCaseKey] ?? null;

  // Demo cases come from the live API so the frontend never carries its own copy of the rules.
  useEffect(() => {
    fetch(`${API_BASE}/api/fixtures`)
      .then((res) => readJson<Record<string, NormalizedCase>>(res))
      .then((data) => {
        setFixtures(data);
        setApiError(null);
      })
      .catch((err: Error) => {
        setApiError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (activeCase) evaluateCurrentCase(activeCase);
  }, [selectedCaseKey, fixtures]);

  const selectDemoCase = (key: string) => {
    setSelectedCaseKey(key);
  };

  const evaluateCurrentCase = async (caseData: NormalizedCase) => {
    setLoading(true);
    setEvaluation(null);
    try {
      const res = await fetch(`${API_BASE}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(caseData),
      });
      setEvaluation(await readJson<RemedyEvaluation>(res));
      setApiError(null);
    } catch (err) {
      setApiError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!evaluation || !activeCase) return;
    setPdfDownloading(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate-package`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case: activeCase, evaluation }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `RemedyAI_Claim_${activeCase.case_id}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert("Failed to download Claim Package PDF from backend service.");
      }
    } catch (err) {
      console.error("PDF download error:", err);
      alert("Error contacting PDF generation service.");
    } finally {
      setPdfDownloading(false);
    }
  };

  const copyNoticeLetter = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedLetter(true);
    setTimeout(() => setCopiedLetter(false), 2500);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation / Brand Banner */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white">RemedyAI</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  Closed-World Engine
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Evidence-Grounded Consumer Coverage Discovery & Claim Preparation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700">
              <Cpu className="w-3.5 h-3.5 text-amber-400" />
              Amazon Bedrock Vision
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700">
              <FileText className="w-3.5 h-3.5 text-sky-400" />
              Amazon Textract AnalyzeExpense
            </span>
            <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              AWS Zero to Shipped • Startup Track
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Value Proposition Hero */}
        <section className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-6 sm:p-8 relative overflow-hidden shadow-xl">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5" />
              Find the coverage you didn't know you had
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
              Post-Warranty Defect? <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-400">
                Discover Verified Protection Pathways Beyond 1 Year
              </span>
            </h1>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              When standard 1-year manufacturer warranties expire, consumers assume they are on their own.
              RemedyAI uses a strict <b>closed-world evidence policy</b> to cross-reference purchase receipts and defect imagery
              against manufacturer service programs, payment-card protections, and statutory consumer law.
            </p>
          </div>
        </section>

        {/* 1-Click Interactive Demo Selector */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Try Real-World Test Scenarios</span>
                <span className="text-xs font-normal text-slate-400">(Zero Setup • 1-Click Evaluation)</span>
              </h2>
              <p className="text-xs text-slate-400">
                Select any verified scenario below to inspect how RemedyAI parses evidence and constructs source-grounded claim packages.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Scenario 1: Apple iPhone 14 Plus */}
            <button
              onClick={() => selectDemoCase('case1_apple_iphone14plus')}
              className={`text-left p-4 rounded-xl border transition-all flex flex-col justify-between ${
                selectedCaseKey === 'case1_apple_iphone14plus'
                  ? 'bg-sky-950/40 border-sky-500 shadow-md shadow-sky-500/10 ring-1 ring-sky-500'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                    <Smartphone className="w-5 h-5" />
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Service Program
                  </span>
                </div>
                <h3 className="font-semibold text-white text-sm">Apple iPhone 14 Plus</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  Rear camera shows no preview ~2.8 yrs after purchase. Finds Apple's active 3-year service program, pending serial check.
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-sky-400 font-medium">
                <span>Inspect Route</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>

            {/* Scenario 2: Sony WH-1000XM5 */}
            <button
              onClick={() => selectDemoCase('case2_visa_infinite_sony')}
              className={`text-left p-4 rounded-xl border transition-all flex flex-col justify-between ${
                selectedCaseKey === 'case2_visa_infinite_sony'
                  ? 'bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <CreditCard className="w-5 h-5" />
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Card Protection
                  </span>
                </div>
                <h3 className="font-semibold text-white text-sm">Sony WH-1000XM5</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  Hinge crack at ~18 months, paid with Visa Infinite. Card benefit can add +1 year to the warranty.
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-indigo-400 font-medium">
                <span>Inspect Route</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>

            {/* Scenario 3: Samsung TV UK */}
            <button
              onClick={() => selectDemoCase('case3_uk_samsung_tv')}
              className={`text-left p-4 rounded-xl border transition-all flex flex-col justify-between ${
                selectedCaseKey === 'case3_uk_samsung_tv'
                  ? 'bg-purple-950/40 border-purple-500 shadow-md shadow-purple-500/10 ring-1 ring-purple-500'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                    <Tv className="w-5 h-5" />
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Statutory Rights
                  </span>
                </div>
                <h3 className="font-semibold text-white text-sm">Samsung 4K TV (UK)</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  Panel lines at ~3 years. Finds the UK Consumer Rights Act 2015 route and the burden-of-proof shift.
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-purple-400 font-medium">
                <span>Inspect Route</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>

            {/* Scenario 4: Unsupported Fallback */}
            <button
              onClick={() => selectDemoCase('case4_unknown_unsupported')}
              className={`text-left p-4 rounded-xl border transition-all flex flex-col justify-between ${
                selectedCaseKey === 'case4_unknown_unsupported'
                  ? 'bg-rose-950/40 border-rose-500 shadow-md shadow-rose-500/10 ring-1 ring-rose-500'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
                    <Coffee className="w-5 h-5" />
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                    Closed-World Fallback
                  </span>
                </div>
                <h3 className="font-semibold text-white text-sm">Espresso Machine</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  Cash purchase, fails after ~3 years. No source matches, so it returns NO VERIFIED COVERAGE.
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-rose-400 font-medium">
                <span>Inspect Fallback</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>
          </div>
        </section>

        {/* Evidence Exhibits & Evaluation Grid */}
        {apiError ? (
          <div role="alert" className="bg-slate-900/80 border border-amber-500/40 rounded-xl p-6 space-y-3">
            <div className="flex items-center gap-2 text-amber-300 font-semibold text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>The RemedyAI engine could not be reached</span>
            </div>
            <p className="text-xs text-slate-300">
              No result is shown because RemedyAI only reports determinations produced by its live evaluation engine.
              Details: <span className="font-mono">{apiError}</span>
            </p>
            <button
              onClick={() => window.location.reload()}
              className="text-xs px-3 py-1.5 rounded-md bg-slate-800 border border-slate-700 text-slate-200 hover:bg-slate-700"
            >
              Retry
            </button>
          </div>
        ) : !activeCase ? (
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-12 text-center">
            <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-sm text-slate-300 mt-3">Loading demo cases from the live API...</p>
          </div>
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Submitted Evidence Exhibits */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4 text-sky-400" />
                  <span>Case Evidence Exhibits</span>
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  ID: {activeCase.case_id}
                </span>
              </div>

              {/* Product Info Summary */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-slate-400 block mb-0.5">Product</label>
                  <p className="font-medium text-slate-200">{activeCase.product_name}</p>
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Retailer / Country</label>
                  <p className="font-medium text-slate-200">{activeCase.retailer} ({activeCase.purchase_country})</p>
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Purchase Date</label>
                  <p className="font-mono text-slate-200">{activeCase.purchase_date}</p>
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Failure Date</label>
                  <p className="font-mono text-slate-200">{activeCase.failure_date}</p>
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Payment Method</label>
                  <p className="font-medium text-slate-200">{activeCase.payment_method || 'Cash / Unrecorded'}</p>
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Standard Warranty</label>
                  <p className="font-medium text-slate-200">{activeCase.original_warranty_years} Year(s)</p>
                </div>
              </div>

              {/* Textract Extraction Exhibit */}
              {activeCase.receipt_data && (
                <div className="bg-slate-950/80 rounded-lg p-3.5 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-sky-400 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" />
                      Receipt data (sample, Textract format)
                    </span>
                    <span className="text-[10px] bg-sky-500/10 text-sky-300 px-1.5 py-0.5 rounded font-mono">
                      Conf: {(activeCase.receipt_data.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs space-y-1 text-slate-300">
                    <p><span className="text-slate-400">Vendor:</span> {activeCase.receipt_data.store_name}</p>
                    <p><span className="text-slate-400">Item:</span> {activeCase.receipt_data.item_description}</p>
                    <p>
                      <span className="text-slate-400">Total:</span>{' '}
                      {activeCase.receipt_data.total_amount != null
                        ? new Intl.NumberFormat('en', {
                            style: 'currency',
                            currency: activeCase.receipt_data.currency || 'USD',
                          }).format(activeCase.receipt_data.total_amount)
                        : 'Not recorded'}
                    </p>
                    <p><span className="text-slate-400">Payment:</span> {activeCase.receipt_data.payment_type}</p>
                  </div>
                </div>
              )}

              {/* Bedrock Vision Exhibit */}
              {activeCase.visual_evidence && (
                <div className="bg-slate-950/80 rounded-lg p-3.5 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" />
                      Visual evidence (sample, Bedrock format)
                    </span>
                    <span className="text-[10px] bg-amber-500/10 text-amber-300 px-1.5 py-0.5 rounded font-mono">
                      Conf: {(activeCase.visual_evidence.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs space-y-1.5 text-slate-300">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Physical Damage:</span>
                      <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                        activeCase.visual_evidence.physical_damage_severity === 'none'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {activeCase.visual_evidence.physical_damage_severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-slate-400 text-[11px]">Visual Observations:</p>
                    <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-300">
                      {activeCase.visual_evidence.visual_observations.map((obs, i) => (
                        <li key={i}>{obs}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Defect Description */}
              <div>
                <label className="text-slate-400 text-xs block mb-1">Reported Defect Description</label>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs text-slate-300 leading-relaxed">
                  "{activeCase.defect_description}"
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Coverage Evaluation & Provenance Trace */}
          <div className="lg:col-span-7 space-y-6">
            {loading ? (
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-12 text-center space-y-3">
                <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-sm text-slate-300">Running Closed-World Evidence Evaluation...</p>
                <p className="text-xs text-slate-400">Cross-referencing verified primary sources and date deltas</p>
              </div>
            ) : evaluation && evaluation.has_coverage && evaluation.matched_routes.length > 0 ? (
              <div className="space-y-6">
                {evaluation.evaluation_date && (
                  <p className="text-[11px] text-slate-400">
                    Program and limitation windows evaluated as of <span className="font-mono">{evaluation.evaluation_date}</span>.
                  </p>
                )}
                {evaluation.notes && evaluation.notes.length > 0 && (
                  <ul className="text-[11px] text-slate-300 bg-slate-900/60 border border-slate-800 rounded-lg p-3 space-y-1">
                    {evaluation.notes.map((note, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {evaluation.matched_routes.map((route) => (
                  <div
                    key={route.route_id}
                    className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-5 shadow-lg"
                  >
                    {/* Header with Status */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                            route.status === 'ELIGIBLE_PENDING_INSPECTION'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                          }`}>
                            {route.status.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-slate-400">• {route.provider}</span>
                        </div>
                        <h2 className="text-lg font-bold text-white mt-1">{route.title}</h2>
                      </div>

                      {/* Download PDF CTA */}
                      <button
                        onClick={handleDownloadPdf}
                        disabled={pdfDownloading}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs shadow-md transition disabled:opacity-50"
                      >
                        {pdfDownloading ? (
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                          <Download className="w-4 h-4" />
                        )}
                        <span>{pdfDownloading ? 'Generating...' : 'Download Claim PDF'}</span>
                      </button>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">{route.summary}</p>

                    {/* Defensible Provenance Trace Model */}
                    <div className="bg-slate-950 rounded-xl p-4 border border-slate-800/90 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800/70 pb-2">
                        <span className="text-xs font-bold text-slate-200 tracking-wide uppercase flex items-center gap-1.5">
                          <ShieldCheck className="w-4 h-4 text-emerald-400" />
                          Auditable Provenance Chain
                        </span>
                        <a
                          href={route.primary_source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 underline"
                        >
                          <span>Primary Source Reference</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      <div className="space-y-3 text-xs">
                        {/* 1. Claim Statement */}
                        <div>
                          <span className="text-slate-400 font-medium block mb-0.5">1. Claim Pathway:</span>
                          <p className="text-emerald-300 font-semibold">{route.provenance.claim}</p>
                        </div>

                        {/* 2. Why Matched */}
                        <div>
                          <span className="text-slate-400 font-medium block mb-0.5">2. Why This Matched (Eligibility Calculation):</span>
                          <p className="text-slate-200 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 leading-relaxed">
                            {route.provenance.why_matched}
                          </p>
                        </div>

                        {/* 3. Documented Evidence */}
                        <div>
                          <span className="text-slate-400 font-medium block mb-1">3. Submitted Evidence Verification:</span>
                          <ul className="space-y-1 pl-1">
                            {route.provenance.evidence.map((ev, i) => (
                              <li key={i} className="flex items-start gap-2 text-slate-300">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                                <span>{ev}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {/* 4. Mandatory Conditions */}
                        <div>
                          <span className="text-slate-400 font-medium block mb-1">4. Mandatory Conditions:</span>
                          <ul className="space-y-1 pl-1">
                            {route.provenance.conditions.map((cond, i) => (
                              <li key={i} className="flex items-start gap-2 text-slate-300">
                                <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                                <span>{cond}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {/* 5. Exceptions & Caveats */}
                        <div>
                          <span className="text-amber-400 font-medium block mb-1 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>5. What Could Invalidate This (Caveats & Exceptions):</span>
                          </span>
                          <ul className="space-y-1 pl-1">
                            {route.provenance.exceptions.map((exc, i) => (
                              <li key={i} className="flex items-start gap-2 text-amber-200/90 bg-amber-500/5 p-1.5 rounded border border-amber-500/10">
                                <span className="text-amber-400 font-bold shrink-0">•</span>
                                <span>{exc}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>

                    {/* Action Plan & Draft Formal Notice */}
                    <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-200">Recommended Action Plan</span>
                        <button
                          onClick={() => {
                            const draft = `To: ${route.provider}\nSubject: Formal Claim Notice - ${activeCase.product_name} (Case: ${activeCase.case_id})\n\nI am writing to formally request remedy regarding my ${activeCase.product_name}, purchased on ${activeCase.purchase_date}. On ${activeCase.failure_date}, the item developed the following defect: "${activeCase.defect_description}".\n\nUnder documented policy criteria for ${route.title} (${route.primary_source.url}), I believe this item may qualify for remedy, subject to your verification. Attached please find proof of purchase, photographic evidence, and payment records.\n\nPlease confirm receipt and provide inspection/repair instructions.`;
                            copyNoticeLetter(draft);
                          }}
                          className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 font-medium"
                        >
                          {copiedLetter ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          <span>{copiedLetter ? 'Copied to Clipboard' : 'Copy Draft Notice'}</span>
                        </button>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{route.recommended_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Closed-World Rejection Card */
              <div className="bg-slate-900/80 border border-rose-500/40 rounded-xl p-6 space-y-5 shadow-lg">
                <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
                  <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400">
                    <ShieldAlert className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      NO VERIFIED COVERAGE FOUND
                    </span>
                    <h2 className="text-base font-bold text-white mt-1">
                      Strict Closed-World Guardrail Enforced
                    </h2>
                  </div>
                </div>

                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p className="bg-rose-500/5 p-3 rounded-lg border border-rose-500/15 text-rose-200">
                    {evaluation?.unmatched_reason ||
                      "The standard 1-year manufacturer warranty has expired, and no active manufacturer service program, payment-card protection, or statutory limitation matches the submitted evidence."}
                  </p>

                  {evaluation?.notes && evaluation.notes.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="font-semibold text-slate-200 block">Sources checked that did not qualify:</span>
                      <ul className="space-y-1 pl-1">
                        {evaluation.notes.map((note, i) => (
                          <li key={i} className="flex items-start gap-2 text-slate-300">
                            <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                            <span>{note}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="space-y-2 pt-2">
                    <span className="font-semibold text-slate-200 block">Recommended Alternative Steps:</span>
                    <ul className="space-y-1.5 pl-1">
                      {evaluation?.next_steps.map((step, i) => (
                        <li key={i} className="flex items-start gap-2 text-slate-300">
                          <ArrowRight className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                          <span>{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400">
                  <b>Why did this happen?</b> RemedyAI will never hallucinate or invent consumer coverage without verifiable primary-source authority.
                </div>
              </div>
            )}
          </div>
        </div>
        )}
      </main>

      {/* Statutory Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-6 text-center text-xs text-slate-400 space-y-2">
        <p className="max-w-4xl mx-auto px-4">
          <b>Consumer Protection Disclaimer:</b> RemedyAI is an informational claim-preparation engine and does not provide formal legal advice or guarantees of repair, replacement, or refund. Determinations are based on documented primary source policies and submitted evidence. Final coverage decisions rest with the respective manufacturer, retailer, or claims administrator.
        </p>
        <p className="text-slate-400 text-[11px]">
          AWS Zero to Shipped Hackathon • Built with Amazon Bedrock, Amazon Textract, AWS Lambda, ReportLab & AWS Amplify
        </p>
      </footer>
    </div>
  );
}

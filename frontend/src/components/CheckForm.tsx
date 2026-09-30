import { useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, Camera, FileText, Loader2, Search, ShieldCheck } from 'lucide-react';
import { api, photoToBase64 } from '../api';
import type { NormalizedCase, ReceiptData, UkRegion, VisualDefectEvidence } from '../types';
import { Combobox } from './Combobox';
import { PAYMENTS, PRODUCTS, faultsFor, storesFor } from '../suggestions';
import { UK_REGIONS } from './labels';
import { DateField } from './DateField';
import { todayIso } from '../dates';

interface Props {
  onSubmit: (c: NormalizedCase) => void;
  busy: boolean;
}

const today = todayIso;

const inputCls =
  'w-full rounded-lg bg-slate-950 border border-slate-600 px-3 py-2.5 text-[15px] text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-400';
const labelCls = 'block text-sm font-medium text-slate-100';
const hintCls = 'text-sm text-slate-400';

const STEPS = ['What broke', 'Photos (optional)', 'Your options'];

export function CheckForm({ onSubmit, busy }: Props) {
  const [step, setStep] = useState<0 | 1>(0);
  const [f, setF] = useState({
    product_name: '',
    purchase_date: '',
    failure_date: today(),
    purchase_country: 'US',
    uk_region: '' as UkRegion | '',
    retailer: '',
    payment_method: '',
    original_warranty_years: 1,
    defect_description: '',
    already_paid_for_repair: false,
  });
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [privacyOk, setPrivacyOk] = useState(false);
  const [receipt, setReceipt] = useState<ReceiptData | null>(null);
  const [visual, setVisual] = useState<VisualDefectEvidence | null>(null);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((p) => ({ ...p, [k]: v }));

  const dateError =
    f.purchase_date && f.failure_date && f.failure_date < f.purchase_date
      ? "The date it broke can't be before the purchase date."
      : null;
  const isUk = f.purchase_country === 'GB';
  const step1Ready =
    f.product_name.trim() && f.defect_description.trim() && f.purchase_date && f.failure_date && !dateError && (!isUk || f.uk_region);

  const readPhotos = async () => {
    setError(null);
    setReading(true);
    try {
      const res = await api.extract({
        receipt_base64: receiptFile ? await photoToBase64(receiptFile) : undefined,
        defect_image_base64: photoFile ? await photoToBase64(photoFile) : undefined,
        product_hint: f.product_name || undefined,
      });
      setReceipt(res.receipt_data);
      setVisual(res.visual_evidence);
      const r = res.receipt_data;
      if (r && r.source === 'textract') {
        setF((p) => ({
          ...p,
          purchase_date: p.purchase_date || (r.purchase_date && /^\d{4}-\d{2}-\d{2}$/.test(r.purchase_date) ? r.purchase_date : ''),
          retailer: p.retailer || r.store_name || '',
          payment_method: p.payment_method || r.payment_type || '',
        }));
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReading(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!step1Ready) {
      setStep(0);
      return;
    }
    onSubmit({
      case_id: `user_${Date.now()}`,
      ...f,
      uk_region: isUk && f.uk_region ? f.uk_region : null,
      original_warranty_years: Number(f.original_warranty_years) || 1,
      // The claim date is the user's own calendar date (not the server's UTC date).
      evaluation_date: todayIso(),
      confirmed_checks: [],
      receipt_data: receipt,
      visual_evidence: visual,
    });
  };

  return (
    <form onSubmit={submit} className="bg-slate-900/80 border border-slate-700 rounded-2xl p-5 sm:p-6 space-y-6" aria-labelledby="check-heading" noValidate>
      <div className="space-y-3">
        <h2 id="check-heading" className="text-lg font-bold text-white">Check your product</h2>
        <ol className="flex flex-wrap gap-2 text-sm" aria-label="Progress">
          {STEPS.map((s, i) => {
            const current = i === step;
            const done = i < step;
            return (
              <li
                key={s}
                aria-current={current ? 'step' : undefined}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${current ? 'border-sky-400 bg-sky-500/15 text-sky-100' : done ? 'border-emerald-500/50 text-emerald-200' : 'border-slate-700 text-slate-400'}`}
              >
                <span className="font-semibold">{i + 1}</span> {s}
              </li>
            );
          })}
        </ol>
      </div>

      {step === 0 && (
        <fieldset className="space-y-4">
          <legend className="sr-only">Step 1: what broke</legend>
          <Combobox
            label="What is the product?"
            hint="Brand and model, for example Apple iPhone 14 Plus. Pick a suggestion or type your own."
            value={f.product_name}
            onChange={(v) => set('product_name', v)}
            suggestions={PRODUCTS}
            required
            maxLength={200}
          />
          <Combobox
            label="What went wrong?"
            hint="Describe what you see or hear. Suggestions change with the product."
            value={f.defect_description}
            onChange={(v) => set('defect_description', v)}
            suggestions={faultsFor(f.product_name)}
            required
            multiline
            maxLength={2000}
          />
          <div className="grid sm:grid-cols-2 gap-4">
            <DateField
              label="When did you buy it?"
              value={f.purchase_date}
              onChange={(v) => set('purchase_date', v)}
              country={f.purchase_country}
              hint="Type it or use the calendar. The date on your receipt."
              required
            />
            <DateField
              label="When did it break?"
              value={f.failure_date}
              onChange={(v) => set('failure_date', v)}
              country={f.purchase_country}
              hint="An approximate date is fine."
              error={dateError}
              required
            />
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="country" className={labelCls}>Where did you buy it?</label>
              <select id="country" className={inputCls} value={f.purchase_country} onChange={(e) => set('purchase_country', e.target.value)}>
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="IN">India</option>
                <option value="CA">Canada</option>
                <option value="AU">Australia</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            {isUk && (
              <div className="space-y-1.5">
                <label htmlFor="uk-region" className={labelCls}>Which part of the UK?</label>
                <select id="uk-region" required className={inputCls} value={f.uk_region} onChange={(e) => set('uk_region', e.target.value as UkRegion | '')}>
                  <option value="">Choose...</option>
                  {UK_REGIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <p className={hintCls}>Scotland allows 5 years to claim; the rest of the UK allows 6.</p>
              </div>
            )}
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Combobox
              label="Which store?"
              hint="Consumer law claims go to the store that sold it."
              value={f.retailer}
              onChange={(v) => set('retailer', v)}
              suggestions={storesFor(f.purchase_country)}
              maxLength={200}
            />
            <Combobox
              label="How did you pay?"
              hint="Some cards, like Visa Infinite, extend the warranty."
              value={f.payment_method}
              onChange={(v) => set('payment_method', v)}
              suggestions={PAYMENTS}
              maxLength={200}
            />
          </div>
          <div className="grid sm:grid-cols-2 gap-4 items-end">
            <div className="space-y-1.5">
              <label htmlFor="warranty" className={labelCls}>Original warranty (years)</label>
              <input id="warranty" type="number" min={0} max={10} step={0.25} className={inputCls} value={f.original_warranty_years} onChange={(e) => set('original_warranty_years', Number(e.target.value))} />
              <p className={hintCls}>Usually 1 year. Check the box or manual.</p>
            </div>
            <label className="flex items-center gap-3 min-h-11 text-[15px] text-slate-100">
              <input type="checkbox" className="w-5 h-5" checked={f.already_paid_for_repair} onChange={(e) => set('already_paid_for_repair', e.target.checked)} />
              I already paid to have it repaired
            </label>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              type="button"
              disabled={!step1Ready}
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-2 min-h-11 px-5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-[15px] disabled:opacity-40"
            >
              Next: photos (optional) <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              type="submit"
              disabled={busy || !step1Ready}
              className="inline-flex items-center gap-2 min-h-11 px-5 rounded-lg border border-slate-500 text-slate-100 hover:bg-slate-800 font-medium text-[15px] disabled:opacity-40"
            >
              <Search className="w-4 h-4" aria-hidden="true" /> Skip photos and check
            </button>
          </div>
          {!step1Ready && (
            <p className={hintCls}>Fill in the product, what went wrong and both dates{isUk ? ', and the part of the UK' : ''} to continue.</p>
          )}
        </fieldset>
      )}

      {step === 1 && (
        <fieldset className="space-y-5">
          <legend className="sr-only">Step 2: optional photos</legend>
          <p className="text-[15px] text-slate-200">
            Photos are optional. You can go straight to your options. A receipt photo lets RemedyAI check your details against it.
          </p>

          <div role="note" className="rounded-xl border border-amber-400/50 bg-amber-500/10 p-4 space-y-2">
            <p className="flex items-center gap-2 font-semibold text-amber-100">
              <ShieldCheck className="w-5 h-5" aria-hidden="true" /> Before you upload
            </p>
            <ul className="list-disc pl-5 space-y-1 text-sm text-amber-50/90">
              <li>Cover or crop out your <b>name, address, card number, loyalty or order numbers</b>, and any faces.</li>
              <li>We only need the <b>store, date, item and price</b> from the receipt.</li>
              <li>For the fault photo, show the fault only. Avoid people, screens with messages, or documents.</li>
            </ul>
            <p className="text-sm text-amber-50/80">
              Nothing is sent until you press "Read photos". Photos are re-saved in your browser first, which removes location
              (GPS) data. RemedyAI does not save them. See <a href="#privacy" className="underline">Privacy</a>.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <label className="space-y-1.5 block">
              <span className={`${labelCls} flex items-center gap-2`}><FileText className="w-4 h-4" aria-hidden="true" /> Receipt photo</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setReceiptFile(e.target.files?.[0] ?? null)} className="block w-full text-sm text-slate-200 file:mr-3 file:min-h-10 file:rounded-lg file:border-0 file:bg-slate-700 file:px-3 file:text-slate-50" />
            </label>
            <label className="space-y-1.5 block">
              <span className={`${labelCls} flex items-center gap-2`}><Camera className="w-4 h-4" aria-hidden="true" /> Photo of the fault</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhotoFile(e.target.files?.[0] ?? null)} className="block w-full text-sm text-slate-200 file:mr-3 file:min-h-10 file:rounded-lg file:border-0 file:bg-slate-700 file:px-3 file:text-slate-50" />
            </label>
          </div>

          <label className="flex items-start gap-3 text-[15px] text-slate-100">
            <input type="checkbox" className="w-5 h-5 mt-0.5" checked={privacyOk} onChange={(e) => setPrivacyOk(e.target.checked)} />
            <span>I've covered anything personal (or I'm happy to share it).</span>
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={readPhotos}
              disabled={reading || !privacyOk || (!receiptFile && !photoFile)}
              className="inline-flex items-center gap-2 min-h-11 px-4 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-50 font-medium text-[15px] disabled:opacity-40"
            >
              {reading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
              {reading ? 'Reading photos...' : 'Read photos'}
            </button>
            {!privacyOk && (receiptFile || photoFile) && <span className={hintCls}>Tick the box above to continue.</span>}
            <span aria-live="polite" className="text-sm text-slate-300">
              {receipt && (receipt.source === 'textract' ? 'Receipt read. Empty fields were filled in; check them. ' : 'The receipt could not be read. ')}
              {visual && (visual.source === 'bedrock' ? 'Fault photo described.' : 'The fault photo could not be analysed.')}
            </span>
          </div>

          {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}

          <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-800">
            <button type="button" onClick={() => setStep(0)} className="inline-flex items-center gap-2 min-h-11 px-4 rounded-lg border border-slate-600 text-slate-100 hover:bg-slate-800 text-[15px] mt-3">
              <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Back
            </button>
            <button type="submit" disabled={busy || reading} className="inline-flex items-center gap-2 min-h-11 px-5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-[15px] disabled:opacity-50 mt-3">
              <Search className="w-4 h-4" aria-hidden="true" />
              {busy ? 'Checking...' : 'See my options'}
            </button>
          </div>
        </fieldset>
      )}

      <p className="text-sm text-slate-400">
        RemedyAI is not legal advice. The maker, card issuer or store makes the final decision.
      </p>
    </form>
  );
}

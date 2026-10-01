import { useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, Camera, Check, FileText, Loader2, Search, ShieldCheck } from 'lucide-react';
import { api, photoToBase64 } from '../api';
import type { NormalizedCase, ReceiptData, UkRegion, VisualDefectEvidence } from '../types';
import { Combobox } from './Combobox';
import { PAYMENTS, PRODUCTS, faultsFor, storesFor } from '../suggestions';
import { UK_REGIONS, formatMoney, humanDate } from './labels';
import { DateField } from './DateField';
import { todayIso } from '../dates';

interface Props {
  onSubmit: (c: NormalizedCase) => void;
  busy: boolean;
  onOpenPrivacy: () => void;
}

const STEPS = ['What broke', 'Photos (optional)'];
const fileCls =
  'block w-full text-sm text-muted file:mr-3 file:min-h-10 file:rounded-full file:border file:border-line-strong file:bg-surface file:px-4 file:font-semibold file:text-ink hover:file:bg-subtle';

export function CheckForm({ onSubmit, busy, onOpenPrivacy }: Props) {
  const [step, setStep] = useState<0 | 1>(0);
  const [f, setF] = useState({
    product_name: '',
    purchase_date: '',
    failure_date: todayIso(),
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
    f.purchase_date && f.failure_date && f.failure_date < f.purchase_date ? "The date it broke can't be before the purchase date." : null;
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
    <form onSubmit={submit} className="card space-y-7 p-6 sm:p-8" aria-labelledby="check-heading" noValidate>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id="check-heading" className="text-xl font-semibold tracking-tight">Check your product</h3>
        <ol className="flex items-center gap-2 text-sm" aria-label="Progress">
          {STEPS.map((s, i) => {
            const current = i === step;
            const done = i < step;
            return (
              <li key={s} aria-current={current ? 'step' : undefined} className={`flex items-center gap-2 rounded-full px-3 py-1 ${current ? 'bg-accent-soft font-semibold text-accent-text' : 'text-faint'}`}>
                <span className={`inline-flex size-5 items-center justify-center rounded-full text-xs ${current || done ? 'bg-accent text-accent-ink' : 'bg-subtle text-faint'}`}>
                  {done ? <Check className="size-3" aria-hidden="true" /> : i + 1}
                </span>
                {s}
              </li>
            );
          })}
        </ol>
      </div>

      {step === 0 && (
        <fieldset className="space-y-5">
          <legend className="sr-only">Step 1: what broke</legend>
          <Combobox
            label="What is the product?"
            hint="Brand and model. Any brand works; Apple and Google Pixel devices also get their maker's warranty and repair programs."
            value={f.product_name}
            onChange={(v) => set('product_name', v)}
            suggestions={PRODUCTS}
            placeholder="e.g. Apple iPhone 14 Plus"
            required
            maxLength={200}
          />
          <Combobox
            label="What went wrong?"
            hint="What you see or hear. Suggestions follow the product."
            value={f.defect_description}
            onChange={(v) => set('defect_description', v)}
            suggestions={faultsFor(f.product_name)}
            required
            multiline
            maxLength={2000}
          />
          <div className="grid gap-5 sm:grid-cols-2">
            <DateField label="When did you buy it?" value={f.purchase_date} onChange={(v) => set('purchase_date', v)} country={f.purchase_country} hint="Type it or use the calendar." required />
            <DateField label="When did it break?" value={f.failure_date} onChange={(v) => set('failure_date', v)} country={f.purchase_country} hint="An approximate date is fine." error={dateError} required />
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="country" className="label">Where did you buy it?</label>
              <select id="country" className="field" value={f.purchase_country} onChange={(e) => set('purchase_country', e.target.value)}>
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
                <label htmlFor="uk-region" className="label">Which part of the UK?</label>
                <select id="uk-region" required className="field" value={f.uk_region} onChange={(e) => set('uk_region', e.target.value as UkRegion | '')}>
                  <option value="">Choose...</option>
                  {UK_REGIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <p className="hint">Scotland allows 5 years to claim; the rest of the UK, 6.</p>
              </div>
            )}
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <Combobox label="Which store?" hint="Consumer-law claims go to the store that sold it." value={f.retailer} onChange={(v) => set('retailer', v)} suggestions={storesFor(f.purchase_country)} maxLength={200} />
            <Combobox label="How did you pay?" hint="Some cards, like Visa Infinite, extend the warranty." value={f.payment_method} onChange={(v) => set('payment_method', v)} suggestions={PAYMENTS} maxLength={200} />
          </div>
          <div className="grid items-end gap-5 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="warranty" className="label">Original warranty (years)</label>
              <input id="warranty" type="number" min={0} max={10} step={0.25} className="field" value={f.original_warranty_years} onChange={(e) => set('original_warranty_years', Number(e.target.value))} />
              <p className="hint">Usually 1 year.</p>
            </div>
            <label className="flex min-h-11 items-center gap-3 text-[15px]">
              <input type="checkbox" className="size-5 accent-[var(--c-accent)]" checked={f.already_paid_for_repair} onChange={(e) => set('already_paid_for_repair', e.target.checked)} />
              I already paid to have it repaired
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t border-line pt-5">
            <button type="button" disabled={!step1Ready} onClick={() => setStep(1)} className="btn-primary">
              Next: photos <ArrowRight className="size-4" aria-hidden="true" />
            </button>
            <button type="submit" disabled={busy || !step1Ready} className="btn-secondary">
              <Search className="size-4" aria-hidden="true" /> Skip photos and check
            </button>
          </div>
          {!step1Ready && (
            <p className="hint">Add the product, what went wrong and both dates{isUk ? ', and the part of the UK' : ''} to continue.</p>
          )}
        </fieldset>
      )}

      {step === 1 && (
        <fieldset className="space-y-5">
          <legend className="sr-only">Step 2: optional photos</legend>
          <p className="text-muted">Optional. A receipt photo lets RemedyAI check your details against it.</p>

          <div role="note" className="space-y-2 rounded-2xl border border-warn-line bg-warn-soft p-4 text-warn-ink">
            <p className="flex items-center gap-2 font-semibold">
              <ShieldCheck className="size-5" aria-hidden="true" /> Before you upload
            </p>
            <p className="text-sm">
              Cover your <b>name, address, card and order numbers</b>, and any faces. We only need the store, date, item and
              price. Nothing is sent until you press "Read photos", location data is removed first, and nothing is stored.{' '}
              <button type="button" onClick={onOpenPrivacy} className="font-semibold underline underline-offset-2">Privacy</button>
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="label flex items-center gap-2"><FileText className="size-4 text-accent-text" aria-hidden="true" /> Receipt photo</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setReceiptFile(e.target.files?.[0] ?? null)} className={fileCls} />
            </label>
            <label className="block space-y-2">
              <span className="label flex items-center gap-2"><Camera className="size-4 text-accent-text" aria-hidden="true" /> Photo of the fault</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhotoFile(e.target.files?.[0] ?? null)} className={fileCls} />
            </label>
          </div>

          <label className="flex items-start gap-3 text-[15px]">
            <input type="checkbox" className="mt-0.5 size-5 accent-[var(--c-accent)]" checked={privacyOk} onChange={(e) => setPrivacyOk(e.target.checked)} />
            <span>I've covered anything personal (or I'm happy to share it).</span>
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={readPhotos} disabled={reading || !privacyOk || (!receiptFile && !photoFile)} className="btn-secondary">
              {reading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
              {reading ? 'Reading photos...' : 'Read photos'}
            </button>
            {!privacyOk && (receiptFile || photoFile) && <span className="hint">Tick the box above to continue.</span>}
            <span aria-live="polite" className="text-sm text-muted">
              {receipt && (receipt.source === 'textract' ? 'Receipt read; see below. ' : 'The receipt could not be read. ')}
              {visual && (visual.source === 'bedrock' ? 'Fault photo described; see below.' : 'The fault photo could not be analysed.')}
            </span>
          </div>

          {error && <p role="alert" className="text-sm font-medium text-bad-ink">{error}</p>}

          {/* What the AI read is shown before it is used, and can be left out. */}
          {(receipt?.source === 'textract' || visual?.source === 'bedrock') && (
            <div className="space-y-4 rounded-2xl border border-line p-4">
              <p className="font-semibold">What was read. Check it before you continue.</p>
              {receipt?.source === 'textract' && (
                <div className="space-y-1.5">
                  <p className="flex items-center gap-2 text-sm font-semibold"><FileText className="size-4 text-accent-text" aria-hidden="true" /> Receipt</p>
                  <p className="text-sm text-muted">
                    Store: <b className="text-ink">{receipt.store_name || 'not read'}</b> · Date: <b className="text-ink">{humanDate(receipt.purchase_date)}</b> · Total:{' '}
                    <b className="text-ink">{formatMoney(receipt.total_amount, receipt.currency)}</b>
                  </p>
                  <p className="hint">Empty details in step 1 were filled from it. Go back to change them.</p>
                  <button type="button" onClick={() => setReceipt(null)} className="btn-ghost min-h-9 text-sm">Don't use the receipt</button>
                </div>
              )}
              {visual?.source === 'bedrock' && (
                <div className="space-y-1.5">
                  <p className="flex items-center gap-2 text-sm font-semibold"><Camera className="size-4 text-accent-text" aria-hidden="true" /> Photo of the fault</p>
                  {visual.visual_observations.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
                      {visual.visual_observations.map((o, i) => <li key={i}>{o}</li>)}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted">Nothing specific was described.</p>
                  )}
                  <button type="button" onClick={() => setVisual(null)} className="btn-ghost min-h-9 text-sm">Don't use this description</button>
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-3 border-t border-line pt-5">
            <button type="button" onClick={() => setStep(0)} className="btn-secondary">
              <ArrowLeft className="size-4" aria-hidden="true" /> Back
            </button>
            <button type="submit" disabled={busy || reading} className="btn-primary">
              <Search className="size-4" aria-hidden="true" /> {busy ? 'Checking...' : 'See my options'}
            </button>
          </div>
        </fieldset>
      )}

      <p className="text-xs text-faint">Not legal advice. The maker, card issuer or store makes the final decision.</p>
    </form>
  );
}

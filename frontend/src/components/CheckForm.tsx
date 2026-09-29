import { useState, type FormEvent } from 'react';
import { Camera, FileText, Loader2, Search } from 'lucide-react';
import { api, photoToBase64 } from '../api';
import type { NormalizedCase, ReceiptData, VisualDefectEvidence } from '../types';

interface Props {
  onSubmit: (c: NormalizedCase) => void;
  busy: boolean;
}

const today = () => new Date().toISOString().slice(0, 10);

const inputCls =
  'w-full rounded-md bg-slate-950 border border-slate-700 px-2.5 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500';

export function CheckForm({ onSubmit, busy }: Props) {
  const [f, setF] = useState({
    product_name: '',
    purchase_date: '',
    failure_date: today(),
    purchase_country: 'US',
    retailer: '',
    payment_method: '',
    original_warranty_years: 1,
    defect_description: '',
    already_paid_for_repair: false,
  });
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [receipt, setReceipt] = useState<ReceiptData | null>(null);
  const [visual, setVisual] = useState<VisualDefectEvidence | null>(null);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof f, v: string | number | boolean) => setF((p) => ({ ...p, [k]: v }));

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
          product_name: p.product_name || r.item_description || '',
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
    onSubmit({
      case_id: `user_${Date.now()}`,
      ...f,
      original_warranty_years: Number(f.original_warranty_years) || 1,
      receipt_data: receipt,
      visual_evidence: visual,
    });
  };

  return (
    <form onSubmit={submit} className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5" aria-labelledby="check-heading">
      <div>
        <h2 id="check-heading" className="font-semibold text-white text-sm">Check your own product</h2>
        <p className="text-xs text-slate-400 mt-1">
          Photos are optional. They are read by Amazon Textract (receipt) and Amazon Bedrock (fault photo), shown to you to
          correct, and not stored.
        </p>
      </div>

      <fieldset className="grid sm:grid-cols-2 gap-3">
        <legend className="sr-only">Photos</legend>
        <label className="text-xs text-slate-300 space-y-1 block">
          <span className="flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" aria-hidden="true" /> Receipt photo</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setReceiptFile(e.target.files?.[0] ?? null)} className="block w-full text-xs text-slate-300 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-slate-100" />
        </label>
        <label className="text-xs text-slate-300 space-y-1 block">
          <span className="flex items-center gap-1.5"><Camera className="w-3.5 h-3.5" aria-hidden="true" /> Photo of the fault</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhotoFile(e.target.files?.[0] ?? null)} className="block w-full text-xs text-slate-300 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-slate-100" />
        </label>
        <div className="sm:col-span-2">
          <button
            type="button"
            onClick={readPhotos}
            disabled={reading || (!receiptFile && !photoFile)}
            className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-md bg-slate-800 border border-slate-600 text-slate-100 hover:bg-slate-700 disabled:opacity-40"
          >
            {reading && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
            {reading ? 'Reading photos...' : 'Read photos and pre-fill'}
          </button>
          {receipt && <span className="ml-3 text-[11px] text-slate-400">Receipt: {receipt.source === 'textract' ? 'read, please check the fields below' : 'could not be read'}</span>}
          {visual && <span className="ml-3 text-[11px] text-slate-400">Photo: {visual.source === 'bedrock' ? 'described' : 'could not be analyzed'}</span>}
        </div>
      </fieldset>

      <fieldset className="grid sm:grid-cols-2 gap-3 text-xs text-slate-300">
        <legend className="sr-only">Purchase and fault details</legend>
        <label className="space-y-1 sm:col-span-2 block">
          <span>Product (brand and model)</span>
          <input required className={inputCls} value={f.product_name} onChange={(e) => set('product_name', e.target.value)} placeholder="e.g. Apple iPhone 14 Plus" />
        </label>
        <label className="space-y-1 block">
          <span>Purchase date</span>
          <input required type="date" max={today()} className={inputCls} value={f.purchase_date} onChange={(e) => set('purchase_date', e.target.value)} />
        </label>
        <label className="space-y-1 block">
          <span>Date it failed</span>
          <input required type="date" max={today()} className={inputCls} value={f.failure_date} onChange={(e) => set('failure_date', e.target.value)} />
        </label>
        <label className="space-y-1 block">
          <span>Country of purchase</span>
          <select className={inputCls} value={f.purchase_country} onChange={(e) => set('purchase_country', e.target.value)}>
            <option value="US">United States</option>
            <option value="GB">United Kingdom</option>
            <option value="IN">India</option>
            <option value="CA">Canada</option>
            <option value="AU">Australia</option>
            <option value="OTHER">Other</option>
          </select>
        </label>
        <label className="space-y-1 block">
          <span>Store</span>
          <input className={inputCls} value={f.retailer} onChange={(e) => set('retailer', e.target.value)} placeholder="e.g. Best Buy" />
        </label>
        <label className="space-y-1 block">
          <span>Paid with</span>
          <input className={inputCls} value={f.payment_method} onChange={(e) => set('payment_method', e.target.value)} placeholder="e.g. Visa Infinite, debit card, cash" />
        </label>
        <label className="space-y-1 block">
          <span>Original warranty (years)</span>
          <input type="number" min={0} max={10} step={0.25} className={inputCls} value={f.original_warranty_years} onChange={(e) => set('original_warranty_years', e.target.value)} />
        </label>
        <label className="space-y-1 sm:col-span-2 block">
          <span>What went wrong?</span>
          <textarea required rows={3} className={inputCls} value={f.defect_description} onChange={(e) => set('defect_description', e.target.value)} placeholder="e.g. The rear camera shows a black screen with no preview." />
        </label>
        <label className="flex items-center gap-2 sm:col-span-2">
          <input type="checkbox" checked={f.already_paid_for_repair} onChange={(e) => set('already_paid_for_repair', e.target.checked)} />
          <span>I already paid to have this repaired</span>
        </label>
      </fieldset>

      {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}

      <button type="submit" disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm disabled:opacity-50">
        <Search className="w-4 h-4" aria-hidden="true" />
        {busy ? 'Checking...' : 'Check for coverage'}
      </button>
    </form>
  );
}

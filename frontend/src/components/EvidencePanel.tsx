import { Camera, FileText } from 'lucide-react';
import type { NormalizedCase } from '../types';
import { UK_REGIONS, formatMoney, humanDate } from './labels';

const SOURCE_BADGE: Record<string, { text: string; cls: string }> = {
  sample: { text: 'Sample data', cls: 'bg-slate-700/70 text-slate-200' },
  textract: { text: 'Read by Amazon Textract', cls: 'bg-sky-500/15 text-sky-300' },
  bedrock: { text: 'Described by Amazon Bedrock', cls: 'bg-amber-500/15 text-amber-300' },
  unavailable: { text: 'Not analyzed', cls: 'bg-rose-500/15 text-rose-300' },
};

function Badge({ source }: { source: string }) {
  const b = SOURCE_BADGE[source] ?? SOURCE_BADGE.sample;
  return <span className={`text-xs px-2 py-0.5 rounded font-medium ${b.cls}`}>{b.text}</span>;
}

function Fact({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-slate-100 font-medium break-words">{value || 'Not given'}</dd>
    </div>
  );
}

export function EvidencePanel({ c }: { c: NormalizedCase }) {
  return (
    <section aria-labelledby="evidence-heading" className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
      <h2 id="evidence-heading" className="font-semibold text-white text-sm flex items-center gap-2">
        <FileText className="w-4 h-4 text-sky-400" aria-hidden="true" />
        What we were told
      </h2>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <Fact label="Product" value={c.product_name} />
        <Fact
          label="Bought from"
          value={`${c.retailer || 'Not given'} (${c.purchase_country}${c.uk_region ? `, ${UK_REGIONS.find((r) => r.value === c.uk_region)?.label}` : ''})`}
        />
        <Fact label="Bought on" value={humanDate(c.purchase_date)} />
        <Fact label="Broke on" value={humanDate(c.failure_date)} />
        <Fact label="Paid with" value={c.payment_method} />
        <Fact label="Original warranty" value={`${c.original_warranty_years} year(s)`} />
      </dl>

      <div>
        <p className="text-slate-400 text-xs mb-1">What went wrong</p>
        <blockquote className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-sm text-slate-200 leading-relaxed">
          {c.defect_description}
        </blockquote>
      </div>

      {c.receipt_data && (
        <div className="bg-slate-950/80 rounded-lg p-3.5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-sky-300 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" aria-hidden="true" /> Receipt
            </span>
            <Badge source={c.receipt_data.source} />
          </div>
          <dl className="text-sm grid grid-cols-2 gap-2">
            <Fact label="Store" value={c.receipt_data.store_name} />
            <Fact label="Date" value={humanDate(c.receipt_data.purchase_date)} />
            <Fact label="Item" value={c.receipt_data.item_description} />
            <Fact label="Total" value={formatMoney(c.receipt_data.total_amount, c.receipt_data.currency)} />
          </dl>
          {c.receipt_data.source === 'textract' && c.receipt_data.confidence_score != null && (
            <p className="text-sm text-slate-400">
              Textract's own confidence on these fields: {(c.receipt_data.confidence_score * 100).toFixed(0)}%
            </p>
          )}
        </div>
      )}

      {c.visual_evidence && (
        <div className="bg-slate-950/80 rounded-lg p-3.5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
              <Camera className="w-3.5 h-3.5" aria-hidden="true" /> Photo of the fault
            </span>
            <Badge source={c.visual_evidence.source} />
          </div>
          <p className="text-sm text-slate-300">
            Visible damage: <b className="text-slate-100">{c.visual_evidence.physical_damage_severity.replace('_', ' ')}</b>
          </p>
          <ul className="list-disc pl-4 space-y-1 text-sm text-slate-300">
            {c.visual_evidence.visual_observations.map((obs, i) => (
              <li key={i}>{obs}</li>
            ))}
          </ul>
          <p className="text-sm text-slate-400">Describes what is visible only. It does not diagnose internal faults.</p>
        </div>
      )}
    </section>
  );
}

import { Camera, FileText } from 'lucide-react';
import type { NormalizedCase } from '../types';
import { UK_REGIONS, formatMoney, humanDate } from './labels';

const SOURCE_BADGE: Record<string, { text: string; cls: string }> = {
  sample: { text: 'Sample data', cls: 'bg-subtle text-muted' },
  textract: { text: 'Read by Amazon Textract', cls: 'bg-accent-soft text-accent-text' },
  bedrock: { text: 'Described by Amazon Bedrock', cls: 'bg-accent-soft text-accent-text' },
  unavailable: { text: 'Not analysed', cls: 'bg-bad-soft text-bad-ink' },
};

function Badge({ source }: { source: string }) {
  const b = SOURCE_BADGE[source] ?? SOURCE_BADGE.sample;
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${b.cls}`}>{b.text}</span>;
}

function Fact({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-0.5 break-words font-medium text-ink">{value || 'Not given'}</dd>
    </div>
  );
}

/** The case as entered (or as the example defines it), with any receipt and photo evidence. */
export function EvidencePanel({ c }: { c: NormalizedCase }) {
  const region = c.uk_region ? UK_REGIONS.find((r) => r.value === c.uk_region)?.label : null;
  return (
    <section aria-labelledby="evidence-heading" className="card space-y-5 p-6">
      <h3 id="evidence-heading" className="text-base font-semibold">The case</h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
        <div className="col-span-2"><Fact label="Product" value={c.product_name} /></div>
        <Fact label="Bought" value={humanDate(c.purchase_date)} />
        <Fact label="Broke" value={humanDate(c.failure_date)} />
        <Fact label="Store" value={`${c.retailer || 'Not given'} (${c.purchase_country}${region ? `, ${region}` : ''})`} />
        <Fact label="Paid with" value={c.payment_method} />
        <div className="col-span-2"><Fact label="What went wrong" value={c.defect_description} /></div>
      </dl>

      {c.receipt_data && (
        <div className="space-y-3 rounded-2xl bg-subtle p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2 text-sm font-semibold"><FileText className="size-4 text-accent-text" aria-hidden="true" /> Receipt</span>
            <Badge source={c.receipt_data.source} />
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Fact label="Store" value={c.receipt_data.store_name} />
            <Fact label="Date" value={humanDate(c.receipt_data.purchase_date)} />
            <Fact label="Item" value={c.receipt_data.item_description} />
            <Fact label="Total" value={formatMoney(c.receipt_data.total_amount, c.receipt_data.currency)} />
          </dl>
          {c.receipt_data.source === 'textract' && c.receipt_data.confidence_score != null && (
            <p className="text-xs text-faint">Textract's own confidence on these fields: {(c.receipt_data.confidence_score * 100).toFixed(0)}%</p>
          )}
        </div>
      )}

      {c.visual_evidence && (
        <div className="space-y-2 rounded-2xl bg-subtle p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2 text-sm font-semibold"><Camera className="size-4 text-accent-text" aria-hidden="true" /> Photo of the fault</span>
            <Badge source={c.visual_evidence.source} />
          </div>
          <p className="text-sm text-muted">Visible damage: <b className="text-ink">{c.visual_evidence.physical_damage_severity.replace('_', ' ')}</b></p>
          {c.visual_evidence.visual_observations.length > 0 && (
            <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
              {c.visual_evidence.visual_observations.map((obs, i) => <li key={i}>{obs}</li>)}
            </ul>
          )}
          <p className="text-xs text-faint">Describes what is visible only. It does not diagnose internal faults.</p>
        </div>
      )}
    </section>
  );
}

import { useEffect, useId, useRef, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { exampleFormat, formatIso, parseTypedDate, todayIso } from '../dates';

interface Props {
  label: string;
  value: string; // YYYY-MM-DD or ''
  onChange: (iso: string) => void;
  country: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
}

const fieldCls = 'field pr-12';

/**
 * A date the user can type (in several formats) or pick from the browser's calendar.
 * The typed text is kept as typed; the parsed date is shown underneath so the user can
 * see exactly how it was read.
 */
export function DateField({ label, value, onChange, country, hint, error, required }: Props) {
  const id = useId();
  const pickerRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(value ? formatIso(value) : '');
  const [touched, setTouched] = useState(false);
  const max = todayIso();

  // Keep the text in sync when the value changes from outside (calendar, receipt pre-fill).
  useEffect(() => {
    if (value && parseTypedDate(text, country) !== value) setText(formatIso(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const parsed = parseTypedDate(text, country);
  const future = parsed && parsed > max;
  const localError = text && !parsed ? `Couldn't read that date. Try ${exampleFormat(country)} or "24 Nov 2023".` : future ? "That date is in the future." : null;
  const shownError = (touched && localError) || error || null;

  const commit = (t: string) => {
    setText(t);
    const iso = parseTypedDate(t, country);
    onChange(iso && iso <= max ? iso : '');
  };

  const openPicker = () => {
    const el = pickerRef.current;
    if (!el) return;
    try {
      el.showPicker();
    } catch {
      el.focus();
      el.click();
    }
  };

  const describedBy = [hint ? `${id}-hint` : '', `${id}-read`, shownError ? `${id}-err` : ''].filter(Boolean).join(' ');

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="label">{label}</label>
      <div className="relative">
        <input
          id={id}
          type="text"
          inputMode="text"
          autoComplete="off"
          required={required}
          value={text}
          placeholder={`${exampleFormat(country)} or 24 Nov 2023`}
          onChange={(e) => commit(e.target.value)}
          onBlur={() => { setTouched(true); if (parsed && !future) setText(formatIso(parsed)); }}
          aria-invalid={!!shownError}
          aria-describedby={describedBy}
          className={fieldCls}
        />
        <button
          type="button"
          onClick={openPicker}
          className="absolute right-1 top-1/2 inline-flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-accent-text hover:bg-accent-soft"
          aria-label={`Choose ${label.toLowerCase()} from a calendar`}
          title="Open calendar"
        >
          <CalendarDays className="w-5 h-5" aria-hidden="true" />
        </button>
        {/* The browser's own calendar, opened by the button above. */}
        <input
          ref={pickerRef}
          type="date"
          tabIndex={-1}
          aria-hidden="true"
          max={max}
          value={value}
          onChange={(e) => { if (e.target.value) { onChange(e.target.value); setText(formatIso(e.target.value)); setTouched(true); } }}
          className="absolute right-1 bottom-0 w-10 h-1 opacity-0 pointer-events-none"
        />
      </div>
      <p id={`${id}-read`} className="text-sm font-medium text-accent-text" aria-live="polite">
        {parsed && !future ? `Read as ${formatIso(parsed)}` : ''}
      </p>
      {hint && <p id={`${id}-hint`} className="hint">{hint}</p>}
      {shownError && <p id={`${id}-err`} role="alert" className="text-sm font-medium text-bad-ink">{shownError}</p>}
    </div>
  );
}

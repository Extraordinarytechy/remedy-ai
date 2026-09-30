import { useId, useMemo, useState, type KeyboardEvent, type ReactNode } from 'react';
import { filterSuggestions, type Suggestion } from '../suggestions';

interface Props {
  label: string;
  hint?: ReactNode;
  value: string;
  onChange: (v: string) => void;
  suggestions: Suggestion[];
  placeholder?: string;
  required?: boolean;
  multiline?: boolean;
  maxLength: number;
}

const fieldCls =
  'w-full rounded-lg bg-slate-950 border border-slate-600 px-3 py-2.5 text-[15px] text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-400';

/** Text input with a suggestion list (WAI-ARIA combobox pattern). Free text is always allowed. */
export function Combobox({ label, hint, value, onChange, suggestions, placeholder, required, multiline, maxLength }: Props) {
  const id = useId();
  const listId = `${id}-list`;
  const hintId = `${id}-hint`;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const matches = useMemo(() => filterSuggestions(suggestions, value), [suggestions, value]);
  const show = open && matches.length > 0;

  const pick = (s: Suggestion) => {
    onChange(s.value);
    setOpen(false);
    setActive(-1);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(a + 1, matches.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, -1));
    } else if (e.key === 'Enter' && show && active >= 0) {
      e.preventDefault();
      pick(matches[active]);
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActive(-1);
    }
  };

  const common = {
    id,
    value,
    required,
    maxLength,
    placeholder,
    role: 'combobox' as const,
    'aria-autocomplete': 'list' as const,
    'aria-expanded': show,
    'aria-controls': listId,
    'aria-activedescendant': show && active >= 0 ? `${listId}-${active}` : undefined,
    'aria-describedby': hint ? hintId : undefined,
    autoComplete: 'off',
    className: fieldCls,
    onFocus: () => setOpen(true),
    onBlur: () => setTimeout(() => setOpen(false), 120),
    onKeyDown,
  };

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-100">
        {label}
      </label>
      <div className="relative">
        {multiline ? (
          <textarea
            rows={3}
            {...common}
            onChange={(e) => { onChange(e.target.value); setOpen(true); setActive(-1); }}
          />
        ) : (
          <input
            type="text"
            {...common}
            onChange={(e) => { onChange(e.target.value); setOpen(true); setActive(-1); }}
          />
        )}
        {show && (
          <ul
            id={listId}
            role="listbox"
            aria-label={`Suggestions for ${label}`}
            className="absolute z-20 mt-1 w-full max-h-60 overflow-auto rounded-lg border border-slate-600 bg-slate-900 shadow-xl"
          >
            {matches.map((s, i) => (
              <li
                key={s.value}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => { e.preventDefault(); pick(s); }}
                onMouseEnter={() => setActive(i)}
                className={`px-3 py-2.5 text-[15px] cursor-pointer flex items-center justify-between gap-3 ${i === active ? 'bg-sky-700 text-white' : 'text-slate-100'}`}
              >
                <Highlight text={s.value} query={value} />
                {s.note && <span className="text-xs text-emerald-300 shrink-0">{s.note}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="sr-only" aria-live="polite">
        {show ? `${matches.length} suggestion${matches.length === 1 ? '' : 's'} available. Use the arrow keys to choose.` : ''}
      </p>
      {hint && <p id={hintId} className="text-sm text-slate-400">{hint}</p>}
    </div>
  );
}

function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim();
  const i = q ? text.toLowerCase().indexOf(q.toLowerCase()) : -1;
  if (i < 0) return <span>{text}</span>;
  return (
    <span>
      {text.slice(0, i)}
      <mark className="bg-transparent text-inherit font-bold underline underline-offset-2">{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </span>
  );
}

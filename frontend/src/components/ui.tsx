import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Moon, Sun, X } from 'lucide-react';

/** Light/dark switch. Light is the default; the choice is kept only in this browser. */
export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0a0f0d' : '#f7f7f5');
    try {
      localStorage.setItem('remedyai-theme', dark ? 'dark' : 'light');
    } catch {
      /* storage unavailable */
    }
  }, [dark]);
  return (
    <button
      type="button"
      onClick={() => setDark((d) => !d)}
      aria-pressed={dark}
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={dark ? 'Light theme' : 'Dark theme'}
      className="inline-flex size-10 items-center justify-center rounded-full border border-line bg-surface text-muted hover:text-ink hover:bg-subtle transition-colors"
    >
      {dark ? <Sun className="size-[18px]" aria-hidden="true" /> : <Moon className="size-[18px]" aria-hidden="true" />}
    </button>
  );
}

/** Accessible modal built on the native <dialog> element (focus trap and Esc come for free). */
export function Modal({
  open, onClose, title, children, wide = false,
}: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => { if (e.target === ref.current) onClose(); }}
      aria-labelledby="modal-title"
      className={`m-auto w-[calc(100%-2rem)] ${wide ? 'max-w-4xl' : 'max-w-2xl'} max-h-[85vh] rounded-3xl border border-line bg-surface p-0 text-ink shadow-2xl`}
    >
      {open && (
        <div className="flex max-h-[85vh] flex-col">
          <div className="flex items-center justify-between gap-4 border-b border-line px-6 py-4">
            <h2 id="modal-title" className="text-lg font-semibold">{title}</h2>
            <button type="button" onClick={onClose} className="inline-flex size-10 items-center justify-center rounded-full text-muted hover:bg-subtle hover:text-ink" aria-label="Close">
              <X className="size-5" aria-hidden="true" />
            </button>
          </div>
          <div className="overflow-y-auto px-6 py-5">{children}</div>
        </div>
      )}
    </dialog>
  );
}

/** Click-to-open section (native <details>, so it works with keyboard and screen readers). */
export function Disclosure({
  title, children, defaultOpen = false, meta,
}: { title: ReactNode; children: ReactNode; defaultOpen?: boolean; meta?: ReactNode }) {
  return (
    <details className="disclosure group" open={defaultOpen}>
      <summary>
        <span className="flex min-w-0 items-center gap-2">{title}</span>
        {meta && <span className="ml-auto text-sm font-normal text-faint">{meta}</span>}
      </summary>
      <div className="px-4 pb-4 text-[15px] text-muted">{children}</div>
    </details>
  );
}

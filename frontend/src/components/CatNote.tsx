/**
 * A small line-drawn cat next to a light one-line joke, shown when a date can't be right
 * (before the model existed, more than 30 years ago, in the future, or broke before it was bought).
 * The drawing is decorative and hidden from screen readers; the real error stays as plain text nearby.
 */
export function CatNote({ joke = "Even our cat can't time-travel." }: { joke?: string }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <svg
        viewBox="0 0 64 64"
        aria-hidden="true"
        focusable="false"
        className="size-14 shrink-0 text-accent-text"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Head with two ears */}
        <path d="M12 28 L10 9 L23 18 Q30 15.5 37 18 L50 9 L48 28 Q49 46 30 47 Q11 46 12 28 Z" />
        {/* Closed, sleepy eyes */}
        <path d="M19 29 Q22 32 25 29" />
        <path d="M35 29 Q38 32 41 29" />
        {/* Nose and mouth */}
        <path d="M28.5 35 L31.5 35 L30 37 Z" />
        <path d="M30 37 Q28 40 25.5 39" />
        <path d="M30 37 Q32 40 34.5 39" />
        {/* Whiskers */}
        <path d="M22 37 L6 34" />
        <path d="M22 39.5 L7 41" />
        <path d="M38 37 L54 34" />
        <path d="M38 39.5 L53 41" />
        {/* A small clock with its hands going nowhere */}
        <circle cx="53" cy="54" r="8" />
        <path d="M53 49 L53 54 L56.5 56" />
      </svg>
      <p className="min-w-0 text-sm text-muted">{joke}</p>
    </div>
  );
}

/**
 * src/components/Workspace.jsx
 * -----------------------------
 * Center column: session notes textarea + submit button.
 *
 * Props
 * -----
 * notes       string
 * setNotes    fn
 * onSubmit    fn
 * isLoading   bool
 * isSignedIn  bool   — button is disabled when false
 */

import { Cpu, ClipboardList, Eraser } from "lucide-react";

const PLACEHOLDER = `Type your rough patient notes here — no formatting needed.

Example:
Patient age 45, male. Lower back pain for 3 days. Pain level 7 out of 10. Muscle spasm present. Applied shortwave diathermy for 15 minutes and basic stretching exercises. Advised rest and follow-up in one week.`;

const CHAR_WARN_THRESHOLD = 80;
const MAX_CHARS           = 2000;

export default function Workspace({ notes, setNotes, onSubmit, isLoading, isSignedIn }) {
  const charCount = notes.length;
  const tooShort  = charCount < CHAR_WARN_THRESHOLD;
  const atLimit   = charCount >= MAX_CHARS;
  // Must be signed in AND have enough text AND not already loading
  const canSubmit = isSignedIn && !isLoading && charCount >= CHAR_WARN_THRESHOLD;

  function handleKey(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canSubmit) onSubmit();
  }

  return (
    <section className="workspace">
      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="workspace__header">
        <div className="workspace__header-left">
          <ClipboardList size={17} strokeWidth={2} />
          <div>
            <h2 className="workspace__title">Session Notes</h2>
            <p className="workspace__subtitle">
              Jot down your patient notes — we'll handle the formatting
            </p>
          </div>
        </div>
        {notes && (
          <button
            className="workspace__clear-btn"
            onClick={() => setNotes("")}
            title="Clear notes"
          >
            <Eraser size={14} />
            Clear
          </button>
        )}
      </div>

      {/* ── Textarea ─────────────────────────────────────────────── */}
      <div className="workspace__editor-wrap">
        <textarea
          className="workspace__textarea"
          value={notes}
          onChange={(e) => setNotes(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKey}
          placeholder={PLACEHOLDER}
          disabled={isLoading}
          spellCheck={false}
          aria-label="Clinical session notes"
        />
        <div className={`workspace__char-count ${atLimit ? "workspace__char-count--limit" : ""}`}>
          {charCount} / {MAX_CHARS}
        </div>
      </div>

      {/* ── Hints ────────────────────────────────────────────────── */}
      {!isSignedIn && (
        <p className="workspace__hint workspace__hint--auth">
          🔐 Please sign in with Google (in the sidebar) to enable document generation.
        </p>
      )}
      {isSignedIn && tooShort && charCount > 0 && (
        <p className="workspace__hint">
          ⚠ Please add a bit more detail — include the patient's age, pain level, and what treatment was applied.
        </p>
      )}

      {/* ── Submit ───────────────────────────────────────────────── */}
      <button
        className={`workspace__submit-btn ${isLoading ? "workspace__submit-btn--loading" : ""}`}
        onClick={onSubmit}
        disabled={!canSubmit}
        title={!isSignedIn ? "Sign in with Google first" : "Ctrl + Enter"}
      >
        {isLoading ? (
          <>
            <span className="workspace__spinner" aria-hidden="true" />
            Generating your document…
          </>
        ) : (
          <>
            <Cpu size={16} strokeWidth={2.5} />
            Generate Case Study
          </>
        )}
      </button>

      {!isLoading && isSignedIn && (
        <p className="workspace__shortcut-hint">
          Tip: press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to submit
        </p>
      )}
    </section>
  );
}
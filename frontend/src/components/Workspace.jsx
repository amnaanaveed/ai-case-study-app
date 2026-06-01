/**
 * src/components/Workspace.jsx
 * -----------------------------
 * Center column: session notes textarea + image upload + submit button.
 */

import { useRef } from "react";
import { Cpu, ClipboardList, Eraser, ImagePlus, X } from "lucide-react";

const PLACEHOLDER = `Type your rough patient notes here — no formatting needed.

Example:
Patient age 45, male. Lower back pain for 3 days. Pain level 7 out of 10. Muscle spasm present. Applied shortwave diathermy for 15 minutes and basic stretching exercises. Advised rest and follow-up in one week.`;

const CHAR_WARN_THRESHOLD = 80;
const MAX_CHARS           = 2000;

export default function Workspace({ notes, setNotes, image, setImage, onSubmit, isLoading, isSignedIn }) {
  const fileInputRef = useRef(null); // File input ko control karne ke liye
  const charCount = notes.length;
  const tooShort  = charCount < CHAR_WARN_THRESHOLD;
  const atLimit   = charCount >= MAX_CHARS;
  
  // 🔥 UPDATE: Ab ya toh notes hon (threshold cross karein) YA picture upload hui ho
  const hasEnoughData = charCount >= CHAR_WARN_THRESHOLD || image !== null;
  const canSubmit = isSignedIn && !isLoading && hasEnoughData;

  function handleKey(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canSubmit) onSubmit();
  }

  // Image upload handle karne ka function
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
    }
  };

  // Image remove karne ka function
  const removeImage = () => {
    setImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <section className="workspace">
      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="workspace__header">
        <div className="workspace__header-left">
          <ClipboardList size={17} strokeWidth={2} />
          <div>
            <h2 className="workspace__title">Session Notes</h2>
            <p className="workspace__subtitle">
              Jot down notes or upload a prescription picture
            </p>
          </div>
        </div>
        
        <div style={{ display: "flex", gap: "10px" }}>
          {/* Hidden File Input */}
          <input
            type="file"
            accept="image/*"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleImageChange}
            disabled={isLoading}
          />
          
          {/* Upload Image Button */}
          <button
            className="workspace__clear-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Upload handwritten notes or prescription"
            disabled={isLoading}
            style={{ backgroundColor: "#e0f2fe", color: "#0369a1", borderColor: "#bae6fd" }}
          >
            <ImagePlus size={14} />
            Add Image
          </button>

          {notes && (
            <button
              className="workspace__clear-btn"
              onClick={() => setNotes("")}
              title="Clear notes"
              disabled={isLoading}
            >
              <Eraser size={14} />
              Clear Text
            </button>
          )}
        </div>
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

      {/* ── Image Preview Area (Agar picture upload hui ho) ──────── */}
      {image && (
        <div style={{
          display: "flex", 
          alignItems: "center", 
          justifyContent: "space-between",
          padding: "10px 15px",
          backgroundColor: "#f0fdf4",
          border: "1px solid #bbf7d0",
          borderRadius: "8px",
          marginTop: "10px",
          marginBottom: "10px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#166534", fontWeight: "500", fontSize: "0.9rem" }}>
            <ImagePlus size={18} />
            <span>{image.name}</span>
          </div>
          <button 
            onClick={removeImage}
            disabled={isLoading}
            style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", display: "flex", alignItems: "center" }}
            title="Remove picture"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* ── Hints ────────────────────────────────────────────────── */}
      {!isSignedIn && (
        <p className="workspace__hint workspace__hint--auth">
          🔐 Please sign in with Google (in the sidebar) to enable document generation.
        </p>
      )}
      {isSignedIn && tooShort && !image && charCount > 0 && (
        <p className="workspace__hint">
          ⚠ Please add a bit more detail, or upload a picture of the notes.
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
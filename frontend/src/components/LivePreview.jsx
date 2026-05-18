/**
 * src/components/LivePreview.jsx
 * --------------------------------
 * Right column: dynamic output panel.
 *
 * States
 * ------
 * idle       → soft waiting illustration
 * loading    → animated pulse skeleton
 * validation → yellow warning card listing missing fields
 * api/network→ red error card
 * success    → green success card + drive link + patient data summary
 *
 * Props
 * -----
 * isLoading   bool
 * result      object | null   Normalised response from api.js
 */

import {
  FileCheck2,
  TriangleAlert,
  ExternalLink,
  ServerCrash,
  WifiOff,
  Hourglass,
  User,
  Thermometer,
  Stethoscope,
  ClipboardCheck,
} from "lucide-react";

// ── Sub-components ────────────────────────────────────────────────── //

function IdleState() {
  return (
    <div className="preview__idle">
      <div className="preview__idle-icon">
        <Hourglass size={32} strokeWidth={1.5} />
      </div>
      <p className="preview__idle-title">Waiting for notes…</p>
      <p className="preview__idle-sub">
        Type your patient notes on the left and click{" "}
        <strong>Generate Case Study</strong> when you're ready.
      </p>
      <div className="preview__idle-dots">
        <span /><span /><span />
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="preview__loading">
      <div className="preview__loading-header">
        <div className="preview__skel preview__skel--title" />
        <div className="preview__skel preview__skel--badge" />
      </div>
      {[100, 80, 90, 65, 75].map((w, i) => (
        <div
          key={i}
          className="preview__skel preview__skel--line"
          style={{ width: `${w}%`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
      <p className="preview__loading-label">
        <span className="preview__loading-dot" />
        Generating your PDF document…
      </p>
    </div>
  );
}

function ValidationError({ result }) {
  return (
    <div className="preview__error preview__error--validation">
      <div className="preview__error-header">
        <TriangleAlert size={20} strokeWidth={2} />
        <h3>Missing Information</h3>
      </div>
      <p className="preview__error-message">{result.message}</p>
      {result.missing?.length > 0 && (
        <div className="preview__missing-list">
          <p className="preview__missing-label">Please add the following:</p>
          <ul>
            {result.missing.map((field, i) => (
              <li key={i}>
                <span className="preview__missing-bullet" />
                {field}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="preview__error-tip">
        Just update your notes to include these details and try again.
      </p>
    </div>
  );
}

function ApiError({ result }) {
  const Icon = result.type === "network" ? WifiOff : ServerCrash;
  const title =
    result.type === "network" ? "Network Error" : "Server Error";

  return (
    <div className="preview__error preview__error--api">
      <div className="preview__error-header">
        <Icon size={20} strokeWidth={2} />
        <h3>{title}</h3>
      </div>
      <p className="preview__error-message">{result.message}</p>
      <p className="preview__error-tip">
        Something went wrong on our end. Please try again in a moment.
      </p>
    </div>
  );
}

function DataPill({ icon: Icon, label, value }) {
  return (
    <div className="preview__pill">
      <Icon size={13} strokeWidth={2} />
      <span className="preview__pill-label">{label}</span>
      <span className="preview__pill-value">{value}</span>
    </div>
  );
}

function BulletGroup({ title, items }) {
  if (!items?.length) return null;
  return (
    <div className="preview__group">
      <p className="preview__group-title">{title}</p>
      <ul className="preview__group-list">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function SuccessState({ result }) {
  const pd = result.patientData ?? {};

  return (
    <div className="preview__success">
      {/* ── Status badge ─────────────────────────────────────────── */}
      <div className="preview__success-badge">
        <FileCheck2 size={16} strokeWidth={2.5} />
        Case Study Generated
      </div>

      {/* ── Drive CTA ────────────────────────────────────────────── */}
      <a
        href={result.driveLink}
        target="_blank"
        rel="noopener noreferrer"
        className="preview__drive-link"
      >
        <span>Open PDF in Google Drive</span>
        <ExternalLink size={15} strokeWidth={2.5} />
      </a>

      {/* ── Patient summary pills ─────────────────────────────────── */}
      <div className="preview__pills">
        <DataPill icon={User}        label="Age"    value={pd.patient_age ?? "—"} />
        <DataPill icon={User}        label="Gender" value={pd.patient_gender ?? "—"} />
        <DataPill icon={Thermometer} label="Pain"   value={`${pd.pain_scale_out_of_10 ?? "—"} / 10`} />
      </div>

      {/* ── Clinical data groups ──────────────────────────────────── */}
      <div className="preview__groups">
        <BulletGroup
          title={<><Stethoscope size={12} /> Symptoms</>}
          items={pd.symptoms}
        />
        <BulletGroup
          title={<><ClipboardCheck size={12} /> Treatment Applied</>}
          items={pd.treatment_applied}
        />
        <BulletGroup
          title={<><ClipboardCheck size={12} /> Recommendations</>}
          items={pd.recommendations}
        />
      </div>

      {/* ── Success message ───────────────────────────────────────── */}
      <p className="preview__success-msg">{result.message}</p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────── //
export default function LivePreview({ isLoading, result }) {
  function renderContent() {
    if (isLoading)                                      return <LoadingState />;
    if (!result)                                        return <IdleState />;
    if (result.type === "validation")                   return <ValidationError result={result} />;
    if (result.type === "api" || result.type === "network") return <ApiError result={result} />;
    if (result.ok)                                      return <SuccessState result={result} />;
    return <IdleState />;
  }

  return (
    <aside className="preview">
      <div className="preview__header">
        <h2 className="preview__title">Document Status</h2>
        <div className={`preview__status-dot ${isLoading ? "preview__status-dot--active" : result?.ok ? "preview__status-dot--success" : result ? "preview__status-dot--error" : ""}`} />
      </div>
      <div className="preview__body">
        {renderContent()}
      </div>
    </aside>
  );
}
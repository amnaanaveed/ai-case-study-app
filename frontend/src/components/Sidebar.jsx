/**
 * src/components/Sidebar.jsx
 * ---------------------------
 * Left column: brand, Google sign-in, New Session, dynamic case history.
 *
 * Props
 * -----
 * onNewSession   () => void
 * recentCases    { id, title, date, driveLink }[]
 * isSignedIn     bool
 * onLoginSuccess (token: string) => void
 * onLogout       () => void
 */

import { useGoogleLogin } from "@react-oauth/google";
import {
  FilePlus2, Activity, Clock, ChevronRight,
  Stethoscope, LogIn, LogOut, ExternalLink,
} from "lucide-react";

// The Drive scope required by the backend to upload on the user's behalf
const DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file";

export default function Sidebar({
  onNewSession,
  recentCases,
  isSignedIn,
  onLoginSuccess,
  onLogout,
}) {
  const login = useGoogleLogin({
    scope:    DRIVE_SCOPE,
    onSuccess: (tokenResponse) => onLoginSuccess(tokenResponse.access_token),
    onError:   (err)           => console.error("Google login failed:", err),
  });

  return (
    <aside className="sidebar">
      {/* ── Brand ──────────────────────────────────────────────────── */}
      <div className="sidebar__brand">
        <div className="sidebar__logo-mark">
          <Stethoscope size={18} strokeWidth={2.5} />
        </div>
        <div className="sidebar__brand-text">
          <span className="sidebar__brand-name">CaseGen</span>
          <span className="sidebar__brand-suffix">AI</span>
        </div>
      </div>

      <div className="sidebar__divider" />

      {/* ── Google Auth ────────────────────────────────────────────── */}
      {isSignedIn ? (
        <div className="sidebar__auth-signed-in">
          <div className="sidebar__auth-badge">
            <span className="sidebar__auth-dot" />
            Connected to Google Drive
          </div>
          <button className="sidebar__logout-btn" onClick={onLogout}>
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      ) : (
        <button className="sidebar__google-btn" onClick={() => login()}>
          {/* Inline SVG Google logo — no external asset needed */}
          <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            <path fill="none" d="M0 0h48v48H0z"/>
          </svg>
          <LogIn size={14} />
          Sign in with Google
        </button>
      )}

      <div className="sidebar__divider" />

      {/* ── New Session ────────────────────────────────────────────── */}
      <button className="sidebar__new-btn" onClick={onNewSession}>
        <FilePlus2 size={15} strokeWidth={2.5} />
        <span>New Session</span>
      </button>

      {/* ── Recent Cases ───────────────────────────────────────────── */}
      <div className="sidebar__section-label">
        <Clock size={12} />
        <span>Recent Cases</span>
      </div>

      <ul className="sidebar__case-list">
        {recentCases.length === 0 ? (
          <li className="sidebar__case-empty">
            No cases yet. Generate your first case study to see it here.
          </li>
        ) : (
          recentCases.map((c) => (
            <li key={c.id} className="sidebar__case-item">
              <div className="sidebar__case-avatar">#</div>
              <div className="sidebar__case-info">
                <p className="sidebar__case-name">{c.title}</p>
                <p className="sidebar__case-date">{c.date}</p>
              </div>
              <a
                href={c.driveLink}
                target="_blank"
                rel="noopener noreferrer"
                className="sidebar__case-link"
                title="Open PDF in Google Drive"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink size={13} />
              </a>
            </li>
          ))
        )}
      </ul>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <div className="sidebar__footer">
        <Activity size={13} />
        <span>{recentCases.length} document{recentCases.length !== 1 ? "s" : ""} generated</span>
      </div>
    </aside>
  );
}
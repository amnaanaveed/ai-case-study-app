/**
 * src/App.jsx
 * ------------
 * Root component — owns all shared state.
 *
 * State
 * -----
 * notes        string   Textarea value
 * isLoading    bool     Pipeline running
 * result       object   Normalised API response
 * accessToken  string   Google OAuth access token (null = not signed in)
 * recentCases  array    Persisted history (localStorage)
 */

import { useState, useCallback } from "react";
import Sidebar     from "./components/Sidebar";
import Workspace   from "./components/Workspace";
import LivePreview from "./components/LivePreview";
import { generateCaseStudy } from "./services/api";

// ── localStorage key ──────────────────────────────────────────────── //
const LS_KEY = "casegen_recent_cases";

function loadCases() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY)) ?? [];
  } catch {
    return [];
  }
}

function saveCases(cases) {
  try {
    // Keep only the 20 most recent entries
    localStorage.setItem(LS_KEY, JSON.stringify(cases.slice(0, 20)));
  } catch {
    // Storage quota exceeded — fail silently
  }
}

export default function App() {
  const [notes,       setNotes]       = useState("");
  const [isLoading,   setIsLoading]   = useState(false);
  const [result,      setResult]      = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [recentCases, setRecentCases] = useState(loadCases);

  // ── Reset workspace ───────────────────────────────────────────────── //
  const handleNewSession = useCallback(() => {
    setNotes("");
    setResult(null);
  }, []);

  // ── Receive token from Sidebar's Google login ─────────────────────── //
  const handleLoginSuccess = useCallback((token) => {
    setAccessToken(token);
  }, []);

  const handleLogout = useCallback(() => {
    setAccessToken(null);
  }, []);

  // ── Pipeline trigger ──────────────────────────────────────────────── //
  const handleSubmit = useCallback(async () => {
    if (!notes.trim() || isLoading || !accessToken) return;

    setIsLoading(true);
    setResult(null);

    try {
      const response = await generateCaseStudy(notes, accessToken);
      setResult(response);

      // ── Push to history on success ───────────────────────────────── //
      if (response.ok && response.driveLink) {
        const pd    = response.patientData ?? {};
        const title = [
          pd.demographics?.name && pd.demographics.name !== "Anonymous"
            ? pd.demographics.name
            : null,
          pd.demographics?.age  ? `Age ${pd.demographics.age}` : null,
          pd.clinical_impression
            ? pd.clinical_impression.split(/[,.(]/)[0].trim()   // first clause only
            : "Case Study",
        ]
          .filter(Boolean)
          .join(" — ")
          .slice(0, 72);                                         // keep it short

        const newCase = {
          id:        Date.now(),
          title:     title || "Case Study",
          date:      new Date().toLocaleDateString("en-GB", {
                       day: "2-digit", month: "short", year: "numeric",
                     }),
          driveLink: response.driveLink,
        };

        setRecentCases((prev) => {
          const updated = [newCase, ...prev];
          saveCases(updated);
          return updated;
        });
      }
    } catch {
      setResult({
        ok:      false,
        type:    "api",
        message: "An unexpected error occurred. Check the browser console.",
      });
    } finally {
      setIsLoading(false);
    }
  }, [notes, isLoading, accessToken]);

  return (
    <div className="app-grid">
      <Sidebar
        onNewSession={handleNewSession}
        recentCases={recentCases}
        isSignedIn={!!accessToken}
        onLoginSuccess={handleLoginSuccess}
        onLogout={handleLogout}
      />
      <Workspace
        notes={notes}
        setNotes={setNotes}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        isSignedIn={!!accessToken}
      />
      <LivePreview
        isLoading={isLoading}
        result={result}
      />
    </div>
  );
}
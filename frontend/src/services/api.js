/**
 * src/services/api.js
 * --------------------
 * Axios service layer.
 *
 * Response contract:
 *   Success    → { ok: true,  driveLink, patientData, message }
 *   Validation → { ok: false, type: "validation", missing, message }
 *   API error  → { ok: false, type: "api",        message }
 *   Network    → { ok: false, type: "network",    message }
 */

import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "https://ai-backend-kx71.onrender.com",
  timeout: 120_000,   // 2 min — enterprise PDF generation can be slow
  headers: { "Content-Type": "application/json" },
});

const GENERATE_ENDPOINT = "/api/v1/generate-case-study";

/**
 * @param {string} notes        Raw clinical notes
 * @param {string} accessToken  Google OAuth access token from useGoogleLogin
 */
export async function generateCaseStudy(notes, accessToken) {
  try {
    const { data } = await client.post(
      GENERATE_ENDPOINT,
      { notes },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    return {
      ok:          true,
      driveLink:   data.drive_link   ?? "",
      patientData: data.patient_data ?? {},
      message:     data.message      ?? "Case study generated successfully.",
    };

  } catch (error) {
    if (error.response?.status === 422) {
      const detail = error.response.data?.detail ?? {};
      return {
        ok:      false,
        type:    "validation",
        missing: Array.isArray(detail.missing) ? detail.missing : [],
        message: detail.message ?? "Clinical notes are missing required information.",
      };
    }

    if (error.response) {
      const detail = error.response.data?.detail;
      return {
        ok:      false,
        type:    "api",
        message: typeof detail === "string"
          ? detail
          : `Server error ${error.response.status}. Please try again.`,
      };
    }

    return {
    ok: false,
    type: "network",
    message: "Cannot reach the live backend. Please check your internet connection."
};
  }
}
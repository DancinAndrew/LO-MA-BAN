/**
 * Persuade API — POST /api/v1/scan/persuade
 * Single input: user_input + first_stage_report; returns persuasion content for preview.
 */

const env = typeof import.meta !== 'undefined' ? (import.meta as { env?: Record<string, string> }).env : undefined
const API_BASE_URL = (env?.VITE_SCOUTNET_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const PERSUADE_API_URL = `${API_BASE_URL}/api/v1/scan/persuade`

export type PersuasionResult = {
  behavior_consequence_warning?: string
  reason_analysis?: {
    is_reasonable?: boolean
    analysis?: string
    empathy_note?: string
  }
  general_warnings?: string[]
  recommended_actions?: string[]
  encouraging_message?: string
  [key: string]: unknown
}

export type FirstStageReportSummary = {
  target_url?: string
  risk_level?: string
  risk_label?: string
  risk_score?: number
  risk_source?: string
  [key: string]: unknown
}

export type PersuasionResponse = {
  user_input: string
  first_stage_report_summary?: FirstStageReportSummary
  second_stage_result: PersuasionResult
}

/**
 * POST /api/v1/scan/persuade
 * Body: { user_input: string, first_stage_report: object }
 * Returns content to show in preview.
 */
export async function callPersuade(
  userInput: string,
  firstStageReport: Record<string, unknown>
): Promise<PersuasionResponse | null> {
  const body = {
    user_input: userInput.trim(),
    first_stage_report: firstStageReport,
  }
  console.log('[ScoutNet] persuade API request:', { url: PERSUADE_API_URL, user_input: body.user_input, first_stage_report_keys: Object.keys(firstStageReport) })
  if (!PERSUADE_API_URL || !PERSUADE_API_URL.startsWith('http')) {
    console.error('[ScoutNet] persuade API URL invalid:', PERSUADE_API_URL)
    return null
  }
  try {
    const res = await fetch(PERSUADE_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const text = await res.text()
    if (!res.ok) {
      console.warn('[ScoutNet] persuade API error:', res.status, text)
      return null
    }
    const data = JSON.parse(text) as PersuasionResponse
    console.log('[ScoutNet] persuade API response:', data)
    return data
  } catch (e) {
    console.warn('[ScoutNet] persuade request failed:', e)
    return null
  }
}

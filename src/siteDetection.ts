/**
 * Site detection — calls backend analyze API and maps response to SiteData + report.
 *
 * Integration:
 * - getSiteData(url): POST url to backend, returns SiteData with report for ScoutNet.
 * - Extension: call from background or popup, pass result to ScoutNet as siteData prop.
 */

/** Report shape from analyze API (report_metadata, kid_friendly_summary, evidence_cards, etc.) */
export type ReportData = {
  report_metadata?: {
    target_url?: string;
    target_domain?: string;
    risk?: { level?: string; score?: number; icon?: string; color?: string; label?: string };
    confidence?: { level?: string; icon?: string; label?: string };
  };
  kid_friendly_summary?: {
    title?: string;
    simple_message?: string;
    short_explanation?: string;
    emoji_reaction?: string;
    action_verb?: string;
  };
  evidence_cards?: Array<{
    id?: string;
    icon?: string;
    title?: string;
    content?: string;
    severity?: string;
  }>;
  safety_tips?: Array<{
    id?: string;
    icon?: string;
    tip?: string;
    why?: string;
    action_text?: string;
  }>;
  next_steps?: Array<{ action?: string; priority?: string; icon?: string; link?: string }>;
  interactive_quiz?: {
    enabled?: boolean;
    question?: string;
    hint?: string;
    options?: Array<{
      id?: string;
      text?: string;
      is_correct?: boolean;
      explanation?: string;
      feedback_icon?: string;
    }>;
    correct_answer_id?: string;
    learning_point?: string;
    difficulty?: string;
  };
  raw_analysis?: {
    risk_level?: string;
    risk_score?: number;
    evidence_analysis?: string[];
    user_warnings?: string[];
    why_unsafe?: string;
  };
};

export type SiteData = {
  currentUrl: string;
  correctUrl: string | null;
  riskScore: string;
  riskLevel: 'low' | 'medium' | 'high';
  warnings: string[];
  /** Full report from analyze API; ScoutNet uses this for UI content */
  report?: ReportData | null;
};

const env = import.meta.env as { VITE_SCOUTNET_API_URL?: string };
const API_BASE = (env?.VITE_SCOUTNET_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const ANALYZE_API_URL = `${API_BASE}/api/v1/scan`;

function normalizeRiskLevel(value: string | undefined): SiteData['riskLevel'] {
  if (!value) return 'low';
  const v = String(value).toLowerCase().trim();
  if (v === 'high') return 'high';
  if (v === 'medium' || v === 'moderate') return 'medium';
  if (v === 'low') return 'low';
  if (v.includes('high') || v === 'danger') return 'high';
  if (v.includes('medium') || v.includes('moderate')) return 'medium';
  return 'low';
}

type AnalyzeApiResponse = {
  target_url?: string;
  final_risk_level?: string;
  risk_score?: number;
  riskScore?: number;
  report?: ReportData;
  /** API may return report at top level (report_metadata, kid_friendly_summary, etc.) */
  report_metadata?: ReportData['report_metadata'];
  kid_friendly_summary?: ReportData['kid_friendly_summary'];
  security_check?: {
    risk_score?: number;
    overall_risk?: string;
    warnings?: string[];
  };
  [key: string]: unknown;
};

function fallbackSafeSiteData(url: string): SiteData {
  return {
    currentUrl: url || 'https://example.com',
    correctUrl: null,
    riskScore: '100/100',
    riskLevel: 'low',
    warnings: [],
    report: null,
  };
}

/**
 * Get detection result by calling the analyze API.
 * Sends POST { url } to backend; response report is attached to SiteData.report.
 */
export async function getSiteData(url?: string): Promise<SiteData> {
  const targetUrl = (url ?? '').trim();
  if (!targetUrl || (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://'))) {
    return fallbackSafeSiteData(targetUrl);
  }

  try {
    console.log('[ScoutNet] analyze request:', { url: targetUrl });
    const res = await fetch(ANALYZE_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: targetUrl }),
    });

    if (!res.ok) {
      console.warn('[ScoutNet] analyze API error:', res.status, await res.text());
      return fallbackSafeSiteData(targetUrl);
    }

    const data = (await res.json()) as AnalyzeApiResponse;
    console.log('[ScoutNet] API response:', data);
    // API may return report as { report: {...} } or as top-level { report_metadata, kid_friendly_summary, ... }
    const report: ReportData | null =
      data.report ?? (data.report_metadata ? (data as unknown as ReportData) : null);
    const riskLevel = normalizeRiskLevel(data.final_risk_level ?? report?.report_metadata?.risk?.level ?? report?.raw_analysis?.risk_level);
    // Prefer API risk score: report.report_metadata.risk.score, then security_check / top-level, then fallback
    const riskScoreNum =
      report?.report_metadata?.risk?.score ??
      data.security_check?.risk_score ??
      data.risk_score ??
      data.riskScore ??
      report?.raw_analysis?.risk_score ??
      (riskLevel === 'low' ? 100 : riskLevel === 'high' ? 20 : 50);
    const riskScore = `${riskScoreNum}/100`;
    const warnings = data.security_check?.warnings ?? report?.raw_analysis?.evidence_analysis ?? report?.raw_analysis?.user_warnings ?? (report?.evidence_cards?.map((c) => c.title ?? c.content).filter(Boolean) as string[]) ?? [];

    const siteData: SiteData = {
      currentUrl: data.target_url ?? report?.report_metadata?.target_url ?? targetUrl,
      correctUrl: null,
      riskScore,
      riskLevel,
      warnings: Array.isArray(warnings) ? warnings : [],
      report: report ?? null,
    };
    console.log('[ScoutNet] mapped SiteData:', { currentUrl: siteData.currentUrl, riskScore: siteData.riskScore, riskLevel: siteData.riskLevel, warningsCount: siteData.warnings.length, hasReport: !!siteData.report });
    return siteData;
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e));
    console.warn('[ScoutNet] analyze request failed:', err.message, { url: ANALYZE_API_URL, cause: err.cause });
    return fallbackSafeSiteData(targetUrl);
  }
}

/** Empty site data when no API result yet. No default/fake content. */
export const EMPTY_SITE_DATA: SiteData = {
  currentUrl: '',
  correctUrl: null,
  riskScore: '0/100',
  riskLevel: 'low',
  warnings: [],
  report: null,
};

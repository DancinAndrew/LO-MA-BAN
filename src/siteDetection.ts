/**
 * Site detection module — ScoutNet web safety detection.
 *
 * Integration points:
 *
 * 1. Frontend (popup / content script)
 *    - For Chrome extension: get current tab URL in popup or content script
 *    - Call getSiteData(currentUrl) or use chrome.runtime.sendMessage to get result from background
 *
 * 2. Background (service worker)
 *    - Implement detection logic in background (blocklist, HTTPS, lookalike URLs, etc.)
 *    - Use chrome.tabs.query for activeTab url, then return SiteData
 *
 * 3. Backend API
 *    - To use a backend: replace with fetch('/api/check-url', { body: url }) and map response to SiteData
 */

export type SiteData = {
  currentUrl: string;
  correctUrl: string | null;
  riskScore: string;
  riskLevel: 'low' | 'medium' | 'high';
  warnings: string[];
};

/** Only these URLs/hosts return high risk (for testing ScoutNet warning); all others are low */
const RISKY_TEST_HOSTS = ['paypa1.com', 'paypa1.example.com', 'evil-phishing.test']

function isTestRiskyUrl(url: string): boolean {
  try {
    const u = new URL(url)
    const host = u.hostname.toLowerCase()
    return RISKY_TEST_HOSTS.some((h) => host === h || host.endsWith('.' + h))
  } catch {
    return false
  }
}

/**
 * Get detection result for the given URL.
 * For integration, replace with: Chrome extension (chrome.tabs.query → background or local check),
 * or fetch your backend API and return SiteData.
 */
export async function getSiteData(url?: string): Promise<SiteData> {
  const targetUrl = url ?? ''
  const isRisky = targetUrl ? isTestRiskyUrl(targetUrl) : false

  if (isRisky) {
    return {
      currentUrl: targetUrl,
      correctUrl: 'paypal.com',
      riskScore: '2/10',
      riskLevel: 'high',
      warnings: [
        'URL typo (paypa1.com is not paypal.com)',
        'Suddenly asks for password',
        'No HTTPS certificate',
      ],
    }
  }

  // Default: safe, don't block
  return {
    currentUrl: targetUrl || 'https://example.com',
    correctUrl: null,
    riskScore: '10/10',
    riskLevel: 'low',
    warnings: [],
  };
}

/**
 * Synchronous default/cached result for React initial render.
 * If you already have data from extension or API, pass it to ScoutNet and skip this.
 */
export function getDefaultSiteData(): SiteData {
  return {
    currentUrl: 'paypa1.com',
    correctUrl: 'paypal.com',
    riskScore: '2/10',
    riskLevel: 'high',
    warnings: [
      'URL typo (paypa1.com is not paypal.com)',
      'Suddenly asks for password',
      'No HTTPS certificate',
    ],
  };
}

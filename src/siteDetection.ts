/**
 * 偵測網站模組 — ScoutNet 網站安全偵測
 *
 * 整合位置說明：
 *
 * 1. 【前端彈出視窗 / 內容腳本】
 *    - 若做 Chrome 擴充：在 popup 或 content script 取得目前分頁 URL
 *    - 呼叫 getSiteData(currentUrl) 或透過 chrome.runtime.sendMessage 向 background 要結果
 *
 * 2. 【背景腳本 (background / service worker)】
 *    - 在 background.js 裡實作實際偵測邏輯（比對惡意網址表、檢查 HTTPS、相似網址等）
 *    - 用 chrome.tabs.query 取得 activeTab 的 url，偵測完回傳 SiteData
 *
 * 3. 【API 後端】
 *    - 若改為透過後端 API 偵測：在此改為 fetch('/api/check-url', { body: url })
 *    - 將 API 回傳結果轉成 SiteData 型別
 */

export type SiteData = {
  currentUrl: string;
  correctUrl: string | null;
  riskScore: string;
  riskLevel: 'low' | 'medium' | 'high';
  warnings: string[];
};

/** 僅對這些網址或 host 回傳高風險（用來測試 ScoutNet 警示）；其餘一律 low */
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
 * 取得目前網址的偵測結果。
 * 整合時請在此改為：
 * - Chrome 擴充：chrome.tabs.query 取 url → 送 background 或本地比對 → 回傳
 * - 或 fetch 你的後端 API → 回傳
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

  // 預設：安全，不擋
  return {
    currentUrl: targetUrl || 'https://example.com',
    correctUrl: null,
    riskScore: '10/10',
    riskLevel: 'low',
    warnings: [],
  };
}

/**
 * 同步取得預設/快取結果（給 React 初次 render 用）。
 * 若已從 extension 或 API 拿到資料，可直接傳入 ScoutNet，不必呼叫此函式。
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

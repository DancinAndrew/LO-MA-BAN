import type { SiteData } from '../siteDetection'
import { getSiteData } from '../siteDetection'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'
const SESSION_KEY_WARNED = 'scoutnet_warned_tab_url'

function isRisky(level: SiteData['riskLevel']): boolean {
  return level === 'high' || level === 'medium'
}

chrome.runtime.onInstalled.addListener(() => {
  console.log('[LO-MA-BAN] extension installed')
})

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'PING') {
    sendResponse({ message: 'PONG from service worker' })
  }
})

/** 監聽分頁網址變更，偵測到風險網站時寫入 session 並開啟擴充警告頁 */
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  const url = changeInfo.url ?? tab.url
  if (!url || !tab.id) return
  // 僅在網址已載入完成時偵測，避免重複觸發
  if (changeInfo.status !== 'complete') return
  // 只處理 http/https
  if (!url.startsWith('http://') && !url.startsWith('https://')) return

  try {
    const siteData = await getSiteData(url)
    if (!isRisky(siteData.riskLevel)) return

    const warnedKey = `${tabId}:${url}`
    const { [SESSION_KEY_WARNED]: lastWarned } = await chrome.storage.session.get(SESSION_KEY_WARNED)
    if (lastWarned === warnedKey) return
    await chrome.storage.session.set({ [SESSION_KEY_WARNED]: warnedKey })
    await chrome.storage.session.set({ [SESSION_KEY_DETECTION]: siteData })

    const warningUrl = chrome.runtime.getURL('src/warning/index.html')
    await chrome.tabs.create({ url: warningUrl })
  } catch (e) {
    console.warn('[LO-MA-BAN] background detection error', e)
  }
})

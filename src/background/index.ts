import type { SiteData } from '../siteDetection'
import { getSiteData } from '../siteDetection'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'
const SESSION_KEY_WARNED = 'scoutnet_warned_tab_url'
const SESSION_KEY_PENDING = 'scoutnet_pending_navigation'
const SESSION_KEY_BYPASS = 'scoutnet_bypass_tab_url'

function isRisky(level: SiteData['riskLevel']): boolean {
  return level === 'high' || level === 'medium'
}

function isHttpUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

type PendingNavigation = {
  tabId: number
  targetUrl: string
  sourceUrl?: string
  siteData: SiteData
  createdAt: number
}

async function setPendingNavigation(pending: PendingNavigation) {
  await chrome.storage.session.set({
    [SESSION_KEY_PENDING]: pending,
    [SESSION_KEY_DETECTION]: pending.siteData,
  })
}

async function redirectTabToWarningPage(tabId: number) {
  const warningUrl = chrome.runtime.getURL('src/warning/index.html')
  await chrome.tabs.update(tabId, { url: warningUrl })
}

chrome.runtime.onInstalled.addListener(() => {
  console.log('[LO-MA-BAN] extension installed')
})

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'PING') {
    sendResponse({ message: 'PONG from service worker' })
    return
  }

  if (message?.type === 'CHECK_URL') {
    ;(async () => {
      const tabId = _sender.tab?.id
      const sourceUrl = _sender.tab?.url
      const targetUrl = typeof message?.url === 'string' ? message.url : ''

      if (typeof tabId !== 'number' || !isHttpUrl(targetUrl)) {
        sendResponse({ ok: false })
        return
      }

      try {
        const siteData = await getSiteData(targetUrl)

        if (isRisky(siteData.riskLevel)) {
          const warnedKey = `${tabId}:${targetUrl}`
          await chrome.storage.session.set({ [SESSION_KEY_WARNED]: warnedKey })

          await setPendingNavigation({
            tabId,
            targetUrl,
            sourceUrl,
            siteData,
            createdAt: Date.now(),
          })

          await redirectTabToWarningPage(tabId)
          sendResponse({ ok: true, decision: 'warn', riskLevel: siteData.riskLevel })
          return
        }

        await chrome.tabs.update(tabId, { url: targetUrl })
        sendResponse({ ok: true, decision: 'allow', riskLevel: siteData.riskLevel })
      } catch (e) {
        console.warn('[LO-MA-BAN] CHECK_URL error', e)
        sendResponse({ ok: false })
      }
    })()
    return true
  }

  if (message?.type === 'PROCEED_TO_URL') {
    ;(async () => {
      try {
        const { [SESSION_KEY_PENDING]: pending } = await chrome.storage.session.get(SESSION_KEY_PENDING)
        const data = pending as PendingNavigation | undefined
        if (!data || typeof data.tabId !== 'number' || !isHttpUrl(data.targetUrl)) {
          sendResponse({ ok: false })
          return
        }

        await chrome.storage.session.set({ [SESSION_KEY_BYPASS]: `${data.tabId}:${data.targetUrl}` })
        await chrome.storage.session.remove([SESSION_KEY_PENDING])
        await chrome.tabs.update(data.tabId, { url: data.targetUrl })

        sendResponse({ ok: true })
      } catch (e) {
        console.warn('[LO-MA-BAN] PROCEED_TO_URL error', e)
        sendResponse({ ok: false })
      }
    })()
    return true
  }
})

/** 監聽分頁網址變更，偵測到風險網站時寫入 session 並開啟擴充警告頁 */
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  const url = changeInfo.url ?? tab.url
  if (!url || !tab.id) return
  // 僅在網址已載入完成時偵測，避免重複觸發
  if (changeInfo.status !== 'complete') return
  // 只處理 http/https
  if (!isHttpUrl(url)) return

  try {
    const { [SESSION_KEY_BYPASS]: bypass } = await chrome.storage.session.get(SESSION_KEY_BYPASS)
    if (bypass === `${tabId}:${url}`) return

    const siteData = await getSiteData(url)
    if (!isRisky(siteData.riskLevel)) return

    const warnedKey = `${tabId}:${url}`
    const { [SESSION_KEY_WARNED]: lastWarned } = await chrome.storage.session.get(SESSION_KEY_WARNED)
    if (lastWarned === warnedKey) return
    await chrome.storage.session.set({ [SESSION_KEY_WARNED]: warnedKey })
    await setPendingNavigation({
      tabId,
      targetUrl: url,
      sourceUrl: undefined,
      siteData,
      createdAt: Date.now(),
    })
    await redirectTabToWarningPage(tabId)
  } catch (e) {
    console.warn('[LO-MA-BAN] background detection error', e)
  }
})

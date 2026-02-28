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
  siteData: SiteData | null
  createdAt: number
}

async function setPendingNavigation(pending: PendingNavigation) {
  await chrome.storage.session.set({
    [SESSION_KEY_PENDING]: pending,
    [SESSION_KEY_DETECTION]: pending.siteData ?? null,
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
        const warnedKey = `${tabId}:${targetUrl}`
        await chrome.storage.session.set({ [SESSION_KEY_WARNED]: warnedKey })
        await setPendingNavigation({
          tabId,
          targetUrl,
          sourceUrl,
          siteData: null,
          createdAt: Date.now(),
        })
        await redirectTabToWarningPage(tabId)
        sendResponse({ ok: true, decision: 'warn' })

        const siteData = await getSiteData(targetUrl)
        if (isRisky(siteData.riskLevel)) {
          await setPendingNavigation({
            tabId,
            targetUrl,
            sourceUrl,
            siteData,
            createdAt: Date.now(),
          })
        } else {
          await chrome.storage.session.remove([SESSION_KEY_PENDING, SESSION_KEY_DETECTION])
          await chrome.tabs.update(tabId, { url: targetUrl })
        }
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
        await chrome.storage.session.remove([SESSION_KEY_PENDING, SESSION_KEY_DETECTION])
        await chrome.tabs.update(data.tabId, { url: data.targetUrl })

        sendResponse({ ok: true })
      } catch (e) {
        console.warn('[LO-MA-BAN] PROCEED_TO_URL error', e)
        sendResponse({ ok: false })
      }
    })()
    return true
  }

  if (message?.type === 'LEAVE_SITE') {
    ;(async () => {
      try {
        const { [SESSION_KEY_PENDING]: pending } = await chrome.storage.session.get(SESSION_KEY_PENDING)
        const data = pending as PendingNavigation | undefined
        if (!data || typeof data.tabId !== 'number') {
          sendResponse({ ok: false })
          return
        }
        const urlToOpen = data.sourceUrl && (data.sourceUrl.startsWith('http://') || data.sourceUrl.startsWith('https://'))
          ? data.sourceUrl
          : 'about:blank'
        await chrome.storage.session.remove([SESSION_KEY_PENDING, SESSION_KEY_DETECTION])
        await chrome.tabs.update(data.tabId, { url: urlToOpen })
        sendResponse({ ok: true })
      } catch (e) {
        console.warn('[LO-MA-BAN] LEAVE_SITE error', e)
        sendResponse({ ok: false })
      }
    })()
    return true
  }
})

/** Stay on same website: redirect to sourceUrl and show "Detecting…" popup there; when API returns, go to warning page or target. */
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return
  const url = details.url
  const tabId = details.tabId
  if (!url || tabId < 0) return
  if (!isHttpUrl(url)) return
  if (url.startsWith(chrome.runtime.getURL(''))) return

  try {
    const { [SESSION_KEY_BYPASS]: bypass } = await chrome.storage.session.get(SESSION_KEY_BYPASS)
    if (bypass === `${tabId}:${url}`) return

    let sourceUrl: string | undefined
    try {
      const tab = await chrome.tabs.get(tabId)
      const current = tab.url
      if (current && current !== url && (current.startsWith('http://') || current.startsWith('https://')))
        sourceUrl = current
    } catch {
      // ignore
    }

    const { [SESSION_KEY_PENDING]: existing } = await chrome.storage.session.get(SESSION_KEY_PENDING)
    const existingPending = existing as PendingNavigation | undefined
    if (existingPending?.tabId === tabId && existingPending.siteData === null && existingPending.sourceUrl === url) {
      return
    }

    const warnedKey = `${tabId}:${url}`
    const { [SESSION_KEY_WARNED]: lastWarned } = await chrome.storage.session.get(SESSION_KEY_WARNED)
    if (lastWarned === warnedKey) return
    await chrome.storage.session.set({ [SESSION_KEY_WARNED]: warnedKey })

    const pending: PendingNavigation = {
      tabId,
      targetUrl: url,
      sourceUrl,
      siteData: null,
      createdAt: Date.now(),
    }
    await setPendingNavigation(pending)

    const showPopupOnPage = sourceUrl && isHttpUrl(sourceUrl)

    if (showPopupOnPage) {
      await chrome.tabs.update(tabId, { url: sourceUrl })
      const onTabComplete = (tid: number, info: { status?: string }) => {
        if (tid !== tabId || info.status !== 'complete') return
        chrome.tabs.onUpdated.removeListener(onTabComplete)
        chrome.tabs.sendMessage(tabId, { type: 'SHOW_DETECTING', targetUrl: url }).catch(() => {})
      }
      chrome.tabs.onUpdated.addListener(onTabComplete)
    } else {
      await redirectTabToWarningPage(tabId)
    }

    const siteData = await getSiteData(url)

    if (showPopupOnPage) {
      chrome.tabs.sendMessage(tabId, { type: 'HIDE_DETECTING' }).catch(() => {})
    }

    if (isRisky(siteData.riskLevel)) {
      await setPendingNavigation({ ...pending, siteData })
      await redirectTabToWarningPage(tabId)
    } else {
      await chrome.storage.session.remove([SESSION_KEY_PENDING, SESSION_KEY_DETECTION])
      await chrome.tabs.update(tabId, { url })
    }
  } catch (e) {
    console.warn('[LO-MA-BAN] onBeforeNavigate detection error', e)
  }
})

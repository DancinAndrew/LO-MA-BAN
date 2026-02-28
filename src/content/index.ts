console.log('[LO-MA-BAN] content script loaded on', window.location.href)

let loadingOverlay: HTMLDivElement | null = null
let inFlight = false

function isHttpUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

function showLoadingOverlay(targetUrl: string) {
  if (loadingOverlay) return
  const popup = document.createElement('div')
  popup.setAttribute('data-scoutnet-loading', 'true')
  popup.style.position = 'fixed'
  popup.style.top = '50%'
  popup.style.left = '50%'
  popup.style.transform = 'translate(-50%, -50%)'
  popup.style.zIndex = '2147483647'
  popup.style.display = 'flex'
  popup.style.flexDirection = 'column'
  popup.style.gap = '0'
  popup.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', sans-serif"
  popup.style.pointerEvents = 'none'

  const card = document.createElement('div')
  card.style.background = '#fff'
  card.style.borderRadius = '12px'
  card.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15), 0 0 1px rgba(0,0,0,0.1)'
  card.style.padding = '12px 16px'
  card.style.color = '#1f2937'
  card.style.display = 'flex'
  card.style.alignItems = 'center'
  card.style.gap = '10px'
  card.style.minWidth = '200px'
  card.style.maxWidth = '320px'

  const spinner = document.createElement('div')
  spinner.style.width = '16px'
  spinner.style.height = '16px'
  spinner.style.flexShrink = '0'
  spinner.style.borderRadius = '999px'
  spinner.style.border = '2px solid rgba(0,0,0,0.1)'
  spinner.style.borderTopColor = '#f59e0b'
  spinner.style.animation = 'scoutnet-spin 0.7s linear infinite'

  const text = document.createElement('div')
  text.style.fontSize = '13px'
  text.style.fontWeight = '600'
  text.style.color = '#334155'
  text.textContent = 'Detecting…'

  const sub = document.createElement('div')
  sub.style.fontSize = '11px'
  sub.style.color = '#64748b'
  sub.style.marginTop = '2px'
  sub.textContent = 'Checking this link. Please wait.'

  const col = document.createElement('div')
  col.appendChild(text)
  col.appendChild(sub)

  card.appendChild(spinner)
  card.appendChild(col)
  popup.appendChild(card)

  const style = document.createElement('style')
  style.textContent = `
@keyframes scoutnet-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
`
  popup.appendChild(style)

  document.documentElement.appendChild(popup)
  loadingOverlay = popup
}

function hideLoadingOverlay() {
  loadingOverlay?.remove()
  loadingOverlay = null
}

chrome.runtime.onMessage.addListener((msg: { type?: string; targetUrl?: string }) => {
  if (msg?.type === 'SHOW_DETECTING') {
    showLoadingOverlay(msg.targetUrl ?? '')
  }
  if (msg?.type === 'HIDE_DETECTING') {
    hideLoadingOverlay()
  }
})

function shouldInterceptClick(e: MouseEvent): boolean {
  if (e.defaultPrevented) return false
  if (e.button !== 0) return false
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return false
  return true
}

function findAnchor(el: Element | null): HTMLAnchorElement | null {
  if (!el) return null
  const anchor = el.closest('a[href]')
  return (anchor instanceof HTMLAnchorElement) ? anchor : null
}

document.addEventListener(
  'click',
  async (e) => {
    if (inFlight) return
    if (!shouldInterceptClick(e)) return

    const anchor = findAnchor(e.target instanceof Element ? e.target : null)
    if (!anchor) return
    if (anchor.target && anchor.target !== '_self') return
    if (anchor.hasAttribute('download')) return

    const targetUrl = anchor.href
    if (!isHttpUrl(targetUrl)) return

    // Ignore hash-only navigation within the same document.
    if (anchor.getAttribute('href')?.startsWith('#')) return

    e.preventDefault()
    inFlight = true
    showLoadingOverlay(targetUrl)

    try {
      const timeoutMs = 4000
      const result = await Promise.race([
        chrome.runtime.sendMessage({ type: 'CHECK_URL', url: targetUrl }),
        new Promise((resolve) => setTimeout(() => resolve({ ok: false, timeout: true }), timeoutMs)),
      ])

      // Background will navigate the tab for allow/warn. If it didn't respond, fail open.
      if (!result || (result as any).ok === false) {
        hideLoadingOverlay()
        window.location.assign(targetUrl)
      }
    } catch {
      hideLoadingOverlay()
      window.location.assign(targetUrl)
    } finally {
      // If navigation happens, the page unloads. If not, allow future clicks.
      setTimeout(() => {
        inFlight = false
      }, 300)
    }
  },
  true,
)

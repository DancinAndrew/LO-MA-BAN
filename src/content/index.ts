console.log('[LO-MA-BAN] content script loaded on', window.location.href)

let loadingOverlay: HTMLDivElement | null = null
let inFlight = false

function isHttpUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

function showLoadingOverlay(targetUrl: string) {
  if (loadingOverlay) return
  const overlay = document.createElement('div')
  overlay.setAttribute('data-scoutnet-loading', 'true')
  overlay.style.position = 'fixed'
  overlay.style.inset = '0'
  overlay.style.zIndex = '2147483647'
  overlay.style.background = 'rgba(0, 0, 0, 0.35)'
  overlay.style.backdropFilter = 'blur(4px)'
  overlay.style.display = 'flex'
  overlay.style.alignItems = 'center'
  overlay.style.justifyContent = 'center'
  overlay.style.padding = '24px'

  const card = document.createElement('div')
  card.style.width = 'min(520px, calc(100vw - 48px))'
  card.style.background = 'rgba(255, 255, 255, 0.96)'
  card.style.borderRadius = '16px'
  card.style.boxShadow = '0 20px 60px rgba(0,0,0,0.25)'
  card.style.padding = '18px 18px 16px'
  card.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', sans-serif"
  card.style.color = '#1f2937'

  const row = document.createElement('div')
  row.style.display = 'flex'
  row.style.alignItems = 'center'
  row.style.gap = '12px'

  const spinner = document.createElement('div')
  spinner.style.width = '18px'
  spinner.style.height = '18px'
  spinner.style.borderRadius = '999px'
  spinner.style.border = '3px solid rgba(0,0,0,0.12)'
  spinner.style.borderTopColor = '#f59e0b'
  spinner.style.animation = 'scoutnet-spin 0.8s linear infinite'

  const title = document.createElement('div')
  title.style.fontWeight = '700'
  title.style.fontSize = '14px'
  title.textContent = 'ScoutNet is checking this link…'

  const subtitle = document.createElement('div')
  subtitle.style.marginTop = '8px'
  subtitle.style.fontSize = '12px'
  subtitle.style.color = '#4b5563'
  subtitle.style.wordBreak = 'break-all'
  subtitle.textContent = targetUrl

  row.appendChild(spinner)
  row.appendChild(title)
  card.appendChild(row)
  card.appendChild(subtitle)
  overlay.appendChild(card)

  const style = document.createElement('style')
  style.textContent = `
@keyframes scoutnet-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
`
  overlay.appendChild(style)

  document.documentElement.appendChild(overlay)
  loadingOverlay = overlay
}

function hideLoadingOverlay() {
  loadingOverlay?.remove()
  loadingOverlay = null
}

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

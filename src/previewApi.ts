/**
 * Preview API — calls backend Playwright screenshot endpoint and returns image for display.
 * Path can be overridden via .env VITE_SCOUTNET_PREVIEW_PATH (default /api/preview-url).
 */

const env = typeof import.meta !== 'undefined' ? (import.meta as { env?: Record<string, string> }).env : undefined
const API_BASE_URL = env?.VITE_SCOUTNET_API_URL || 'http://localhost:8000'
const PREVIEW_PATH = env?.VITE_SCOUTNET_PREVIEW_PATH || '/api/preview-url'

const PREVIEW_TIMEOUT_MS = 20000

/** Full preview API URL (for debugging / error messages). */
export const PREVIEW_API_URL = `${API_BASE_URL.replace(/\/$/, '')}${PREVIEW_PATH.startsWith('/') ? PREVIEW_PATH : `/${PREVIEW_PATH}`}`

/**
 * Request a preview image for the given URL (Playwright screenshot).
 * Returns a data URL (data:image/png;base64,...) or null on failure/timeout.
 */
export async function getPreviewImage(targetUrl: string): Promise<string | null> {
  if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) return null

  const url = PREVIEW_API_URL

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), PREVIEW_TIMEOUT_MS)

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: targetUrl }),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)

    if (!res.ok) return null
    const data = (await res.json()) as { image?: string; imageBase64?: string }
    const base64 = data.image ?? data.imageBase64
    if (typeof base64 !== 'string') return null
    return `data:image/png;base64,${base64}`
  } catch {
    return null
  }
}

import React, { useCallback, useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import ScoutNet from '../components/ScoutNet'
import type { SiteData } from '../siteDetection'
import { EMPTY_SITE_DATA } from '../siteDetection'
import { getPreviewImage, PREVIEW_API_URL } from '../previewApi'
import '../styles/ScoutNet.css'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'
const SESSION_KEY_PENDING = 'scoutnet_pending_navigation'

type PendingNavigation = {
  tabId: number
  targetUrl: string
  sourceUrl?: string
  siteData: SiteData | null
  createdAt: number
}

type ProceedStep = 'idle' | 'reason' | 'preview'

function WarningApp() {
  const [siteData, setSiteData] = useState<SiteData | null>(null)
  const [pending, setPending] = useState<PendingNavigation | null>(null)
  const [loading, setLoading] = useState(true)
  const [proceedStep, setProceedStep] = useState<ProceedStep>('idle')
  const [reasonToVisit, setReasonToVisit] = useState('')
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState(false)
  const [previewUrlInvalid, setPreviewUrlInvalid] = useState(false)

  const readSession = useCallback(() => {
    return chrome.storage.session.get([SESSION_KEY_DETECTION, SESSION_KEY_PENDING]).then((result) => {
      const p = result[SESSION_KEY_PENDING] as PendingNavigation | undefined
      setPending(p ?? null)
      const data = p?.siteData ?? (result[SESSION_KEY_DETECTION] as SiteData | undefined)
      setSiteData(data ?? null)
    })
  }, [])

  useEffect(() => {
    readSession().then(() => setLoading(false))
  }, [readSession])

  useEffect(() => {
    const listener = (
      changes: { [key: string]: chrome.storage.StorageChange },
      areaName: string
    ) => {
      if (areaName !== 'session') return
      if (SESSION_KEY_DETECTION in changes || SESSION_KEY_PENDING in changes) readSession()
    }
    chrome.storage.onChanged.addListener(listener)
    return () => chrome.storage.onChanged.removeListener(listener)
  }, [readSession])

  const onLeaveSite = useCallback(() => {
    chrome.runtime.sendMessage({ type: 'LEAVE_SITE' })
  }, [])

  /** When user clicks "I still want to go": show reason input step first */
  const onProceedToUrl = useCallback(() => {
    if (!pending?.targetUrl) return
    setReasonToVisit('')
    setProceedStep('reason')
  }, [pending?.targetUrl])

  /** Submit reason and show preview + dangers */
  const onSubmitReason = useCallback(async () => {
    if (!pending?.targetUrl) return
    const url = pending.targetUrl
    const isHttp = url.startsWith('http://') || url.startsWith('https://')
    const isExtension = url.startsWith('chrome-extension://') || url.startsWith('moz-extension://')
    setProceedStep('preview')
    setPreviewLoading(true)
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(!isHttp || isExtension)
    if (!isHttp || isExtension) {
      setPreviewLoading(false)
      return
    }
    const dataUrl = await getPreviewImage(url)
    setPreviewLoading(false)
    if (dataUrl) setPreviewImage(dataUrl)
    else setPreviewError(true)
  }, [pending?.targetUrl])

  const onCancelReason = useCallback(() => {
    setProceedStep('idle')
    setReasonToVisit('')
  }, [])

  const onConfirmProceed = useCallback(async () => {
    setProceedStep('idle')
    setReasonToVisit('')
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(false)
    await chrome.runtime.sendMessage({ type: 'PROCEED_TO_URL' })
  }, [])

  /** Back = user chose to leave the website (same as "Leave site") */
  const onClosePreview = useCallback(() => {
    setProceedStep('idle')
    setReasonToVisit('')
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(false)
    onLeaveSite()
  }, [onLeaveSite])

  if (loading) {
    return (
      <div className="scoutnet-container" style={{ justifyContent: 'center' }}>
        <p style={{ fontFamily: 'inherit', fontSize: '1rem' }}>Loading…</p>
      </div>
    )
  }

  const detecting = Boolean(pending && siteData === null)

  if (detecting) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent' }}>
        <div
          style={{
            background: '#fff',
            borderRadius: 12,
            boxShadow: '0 4px 20px rgba(0,0,0,0.15), 0 0 1px rgba(0,0,0,0.1)',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            minWidth: 200,
            maxWidth: 320,
          }}
        >
          <div
            style={{
              width: 16,
              height: 16,
              flexShrink: 0,
              borderRadius: '999px',
              border: '2px solid rgba(0,0,0,0.1)',
              borderTopColor: '#f59e0b',
              animation: 'scoutnet-spin 0.7s linear infinite',
            }}
          />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Detecting…</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Checking this link. Please wait.</div>
          </div>
        </div>
      </div>
    )
  }

  const data = siteData ?? pending?.siteData ?? EMPTY_SITE_DATA

  return (
    <>
      <ScoutNet
        siteData={siteData ?? undefined}
        onLeaveSite={onLeaveSite}
        onProceedToUrl={onProceedToUrl}
      />
      {/* Step 1: Why do you want to visit? */}
      {proceedStep === 'reason' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 16,
              maxWidth: 480,
              width: '100%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              padding: 24,
            }}
          >
            <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>Why do you want to visit this site?</h3>
            <p style={{ margin: '0 0 16px', fontSize: 14, color: '#64748b' }}>
              Tell us in your own words. We’ll then show you a preview and remind you of the risks.
            </p>
            <textarea
              value={reasonToVisit}
              onChange={(e) => setReasonToVisit(e.target.value)}
              placeholder="e.g. I need to check something for school"
              rows={3}
              style={{
                width: '100%',
                padding: 12,
                borderRadius: 8,
                border: '1px solid #e2e8f0',
                fontSize: 14,
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 16 }}>
              <button
                type="button"
                onClick={onCancelReason}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontSize: 14,
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onSubmitReason}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: '#f59e0b',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Step 2: Preview + dangers + confirm */}
      {proceedStep === 'preview' && (
        <div
          className="scoutnet-preview-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxSizing: 'border-box',
          }}
        >
          <div
            className="scoutnet-preview-modal"
            style={{
              background: '#fff',
              borderRadius: 16,
              maxWidth: 720,
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              padding: 24,
            }}
          >
            <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>Preview and risks: confirm before visiting</h3>
            {pending?.targetUrl && (
              <p style={{ margin: '0 0 12px', fontSize: 12, color: '#64748b', wordBreak: 'break-all' }}>
                URL: {pending.targetUrl}
              </p>
            )}
            {reasonToVisit.trim() && (
              <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8 }}>
                <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>You said:</p>
                <p style={{ margin: '4px 0 0', fontSize: 14, color: '#334155' }}>{reasonToVisit.trim()}</p>
              </div>
            )}
            {/* Dangers of this site */}
            <div style={{ marginBottom: 16, padding: 12, background: '#fef2f2', borderRadius: 8, border: '1px solid #fecaca' }}>
              <p style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600, color: '#991b1b' }}>⚠️ Risks of this site</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: data.warnings.length > 0 ? 8 : 0 }}>
                <span style={{ fontSize: 13, color: '#b91c1c' }}>
                  Safety: {data.riskScore} · {data.riskLevel === 'high' ? 'High risk' : data.riskLevel === 'medium' ? 'Medium risk' : 'Low risk'}
                </span>
              </div>
              {data.warnings.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#991b1b' }}>
                  {data.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}
              {data.correctUrl && (
                <p style={{ margin: '8px 0 0', fontSize: 12, color: '#b91c1c' }}>
                  The real site you may want is: {data.correctUrl}
                </p>
              )}
            </div>
            {previewUrlInvalid && !previewLoading && (
              <p style={{ margin: 0, padding: '12px', background: '#fef2f2', borderRadius: 8, fontSize: 14, color: '#991b1b' }}>
                This URL cannot be previewed (only http/https supported). You can still click "Confirm" to visit.
              </p>
            )}
            {!previewUrlInvalid && previewLoading && (
              <p style={{ margin: 0, color: '#64748b' }}>Loading preview…</p>
            )}
            {!previewUrlInvalid && previewError && !previewLoading && (
              <p style={{ margin: 0, padding: '12px', background: '#f8fafc', borderRadius: 8, fontSize: 14, color: '#475569' }}>
                Preview is optional. If the backend is not running, you can skip and click "Confirm" to visit.
                <br />
                <span style={{ fontSize: 12, color: '#94a3b8', wordBreak: 'break-all' }}>Backend: {PREVIEW_API_URL}</span>
              </p>
            )}
            {!previewUrlInvalid && previewImage && !previewLoading && (
              <img
                src={previewImage}
                alt="Site preview"
                style={{ width: '100%', height: 'auto', borderRadius: 8, display: 'block', marginBottom: 16 }}
              />
            )}
            <p style={{ margin: '0 0 16px', fontSize: 14, color: '#64748b' }}>
              Are you sure you want to visit this site?
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={onClosePreview}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontSize: 14,
                }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={onConfirmProceed}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: '#f59e0b',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WarningApp />
  </React.StrictMode>,
)

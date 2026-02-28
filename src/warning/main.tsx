import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import ScoutNet from '../components/ScoutNet'
import type { SiteData } from '../siteDetection'
import { getDefaultSiteData } from '../siteDetection'
import '../styles/ScoutNet.css'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'
const SESSION_KEY_PENDING = 'scoutnet_pending_navigation'

type PendingNavigation = {
  tabId: number
  targetUrl: string
  sourceUrl?: string
  siteData: SiteData
  createdAt: number
}

function WarningApp() {
  const [siteData, setSiteData] = useState<SiteData | null>(null)
  const [targetUrl, setTargetUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [proceeding, setProceeding] = useState(false)

  useEffect(() => {
    chrome.storage.session.get([SESSION_KEY_DETECTION, SESSION_KEY_PENDING]).then((result) => {
      const pending = result[SESSION_KEY_PENDING] as PendingNavigation | undefined
      const data = (pending?.siteData ?? (result[SESSION_KEY_DETECTION] as SiteData | undefined)) ?? getDefaultSiteData()
      setSiteData(data)
      setTargetUrl(pending?.targetUrl ?? null)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="scoutnet-container" style={{ justifyContent: 'center' }}>
        <p style={{ fontFamily: 'inherit', fontSize: '1rem' }}>載入中…</p>
      </div>
    )
  }

  return (
    <>
      {targetUrl && (
        <div
          style={{
            position: 'fixed',
            top: 14,
            left: 14,
            right: 14,
            zIndex: 9999,
            display: 'flex',
            gap: 10,
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 10,
            borderRadius: 14,
            background: 'rgba(255, 255, 255, 0.92)',
            boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
            backdropFilter: 'blur(10px)',
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft JhengHei', sans-serif",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, color: '#374151', fontWeight: 700 }}>即將前往</div>
            <div style={{ fontSize: 12, color: '#6b7280', wordBreak: 'break-all' }}>{targetUrl}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <button
              type="button"
              onClick={() => window.history.back()}
              style={{
                border: '1px solid rgba(0,0,0,0.12)',
                background: 'white',
                borderRadius: 12,
                padding: '10px 12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              返回上一頁
            </button>
            <button
              type="button"
              disabled={proceeding}
              onClick={async () => {
                setProceeding(true)
                const res = await chrome.runtime.sendMessage({ type: 'PROCEED_TO_URL' })
                if (!res?.ok) setProceeding(false)
              }}
              style={{
                border: '1px solid rgba(245, 158, 11, 0.35)',
                background: proceeding ? 'rgba(245, 158, 11, 0.55)' : '#f59e0b',
                color: '#111827',
                borderRadius: 12,
                padding: '10px 12px',
                fontWeight: 800,
                cursor: proceeding ? 'not-allowed' : 'pointer',
              }}
            >
              {proceeding ? '前往中…' : '仍要前往'}
            </button>
          </div>
        </div>
      )}
      <ScoutNet siteData={siteData ?? undefined} />
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WarningApp />
  </React.StrictMode>,
)

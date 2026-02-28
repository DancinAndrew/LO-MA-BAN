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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    chrome.storage.session.get([SESSION_KEY_DETECTION, SESSION_KEY_PENDING]).then((result) => {
      const pending = result[SESSION_KEY_PENDING] as PendingNavigation | undefined
      const data = (pending?.siteData ?? (result[SESSION_KEY_DETECTION] as SiteData | undefined)) ?? getDefaultSiteData()
      setSiteData(data)
      setLoading(false)
    })
  }, [])

  const onLeaveSite = () => window.history.back()
  const onProceedToUrl = async () => {
    await chrome.runtime.sendMessage({ type: 'PROCEED_TO_URL' })
  }

  if (loading) {
    return (
      <div className="scoutnet-container" style={{ justifyContent: 'center' }}>
        <p style={{ fontFamily: 'inherit', fontSize: '1rem' }}>載入中…</p>
      </div>
    )
  }

  return (
    <ScoutNet
      siteData={siteData ?? undefined}
      onLeaveSite={onLeaveSite}
      onProceedToUrl={onProceedToUrl}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WarningApp />
  </React.StrictMode>,
)

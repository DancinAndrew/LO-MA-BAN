import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import ScoutNet from '../components/ScoutNet'
import type { SiteData } from '../siteDetection'
import { getDefaultSiteData } from '../siteDetection'
import '../styles/ScoutNet.css'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'

function WarningApp() {
  const [siteData, setSiteData] = useState<SiteData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    chrome.storage.session.get(SESSION_KEY_DETECTION).then((result) => {
      const data = result[SESSION_KEY_DETECTION] as SiteData | undefined
      setSiteData(data ?? getDefaultSiteData())
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

  return <ScoutNet siteData={siteData ?? undefined} />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WarningApp />
  </React.StrictMode>,
)

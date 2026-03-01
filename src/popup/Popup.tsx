import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY_DETECTION_ENABLED = 'scoutnet_detection_enabled'

export function Popup() {
  const [detectionEnabled, setDetectionEnabled] = useState(true)

  useEffect(() => {
    chrome.storage.local.get(STORAGE_KEY_DETECTION_ENABLED, (data) => {
      setDetectionEnabled(data[STORAGE_KEY_DETECTION_ENABLED] !== false)
    })
  }, [])

  const setEnabled = useCallback((on: boolean) => {
    setDetectionEnabled(on)
    chrome.storage.local.set({ [STORAGE_KEY_DETECTION_ENABLED]: on })
    if (typeof chrome.action !== 'undefined') {
      if (on) {
        chrome.action.setBadgeText({ text: 'ON' })
        chrome.action.setBadgeBackgroundColor({ color: '#7cb87c' })
      } else {
        chrome.action.setBadgeText({ text: '' })
      }
    }
  }, [])

  const iconUrl =
    typeof chrome !== 'undefined' && chrome.runtime?.getURL
      ? chrome.runtime.getURL('icons/icon-48.png')
      : ''

  return (
    <main className="popup popup--cute">
      <header className="popup-header">
        {iconUrl ? (
          <img src={iconUrl} alt="" className="popup-icon" aria-hidden />
        ) : null}
        <h1 className="popup-title">ScoutNet</h1>
        <p className="popup-subtitle">Site detection</p>
      </header>
      <section className="popup-toggle-section">
        <div className="popup-turn-row">
          <button
            type="button"
            className={`popup-turn-btn ${!detectionEnabled ? 'popup-turn-btn--active' : ''}`}
            onClick={() => setEnabled(false)}
          >
            Turn Off
          </button>
          <button
            type="button"
            className={`popup-turn-btn ${detectionEnabled ? 'popup-turn-btn--active' : ''}`}
            onClick={() => setEnabled(true)}
          >
            Turn On
          </button>
        </div>
        <p className="popup-hint">
          {detectionEnabled ? 'Detection is on · You’re protected' : 'Detection is off'}
        </p>
      </section>
    </main>
  )
}

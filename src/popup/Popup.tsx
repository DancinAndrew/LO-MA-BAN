import { useState } from 'react'

export function Popup() {
  const [message, setMessage] = useState('Ready')

  const sendPing = async () => {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'PING' })
      setMessage(response?.message ?? 'No response')
    }
    catch (error) {
      setMessage(`Error: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  return (
    <main className="popup">
      <h1>LO-MA-BAN</h1>
      <p>{message}</p>
      <button type="button" onClick={sendPing}>
        Ping Background
      </button>
    </main>
  )
}

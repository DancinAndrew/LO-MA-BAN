chrome.runtime.onInstalled.addListener(() => {
  console.log('[LO-MA-BAN] extension installed')
})

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'PING') {
    sendResponse({ message: 'PONG from service worker' })
  }
})

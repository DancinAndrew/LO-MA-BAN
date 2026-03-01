import { defineManifest } from '@crxjs/vite-plugin'

export default defineManifest({
  manifest_version: 3,
  name: 'LO-MA-BAN',
  description: 'Chrome extension scaffold powered by Vite + CRXJS + React + TypeScript.',
  version: '0.9.0',
  action: {
    default_popup: 'src/popup/index.html',
  },
  background: {
    service_worker: 'src/background/index.ts',
    type: 'module',
  },
  content_scripts: [
    {
      matches: ['<all_urls>'],
      js: ['src/content/index.ts'],
      run_at: 'document_idle',
    },
  ],
  permissions: ['storage', 'activeTab', 'tabs', 'webNavigation'],
  host_permissions: [
    'http://localhost:8000/*',
    'http://127.0.0.1:8000/*',
    'https://lo-ma-ban-production.up.railway.app/*',
  ],
  icons: {
    '16': 'icons/icon-16.png',
    '48': 'icons/icon-48.png',
    '128': 'icons/icon-128.png',
  },
})

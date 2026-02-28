# 前端開發指南 (Frontend Development Guide)

## 1. 架構總覽

本專案採用 **React 18 + TypeScript** 作為 UI 框架，並透過 **Vite + CRXJS** 整合至 Chrome Extension 環境。

### 目錄結構

```text
src/
├── popup/               # 點擊擴充功能圖示時彈出的視窗
│   ├── components/      # 共用元件 (Button, Input, etc.)
│   ├── hooks/           # Custom Hooks (useStorage, useMessage)
│   ├── pages/           # 頁面路由 (若 Popup 內有多頁切換)
│   ├── Popup.tsx        # Popup 入口元件
│   └── main.tsx         # React 掛載點
├── options/             # 選項頁面 (如需設定頁)
│   └── ...
├── content/             # 注入網頁的腳本 (可操作 DOM)
│   └── components/      # 注入頁面的 React 元件 (如浮動視窗)
└── styles/              # 全域樣式 / Tailwind (若有引入)
```

---

## 2. 開發流程 (Workflow)

1. **啟動開發伺服器**
   ```bash
   pnpm dev
   ```
   - 此指令會啟動 Vite HMR，修改 UI 程式碼後，Popup 會自動刷新。
   - **注意**：若修改 `manifest.config.ts` 或 `vite.config.ts`，需重啟 server。

2. **開發 Popup / Options UI**
   - 與一般 React 開發無異。
   - 支援 CSS Modules / Global CSS。
   - 圖片資源請放在 `public/` 或透過 `import` 引入。

3. **開發 Content Script UI (Shadow DOM)**
   - 若要在網頁上注入 UI (例如側邊欄或浮動按鈕)，建議使用 **Shadow DOM** 隔離樣式，避免被宿主網頁 CSS 污染。
   - 範例：
     ```tsx
     import { createRoot } from 'react-dom/client'
     
     const container = document.createElement('div')
     const shadowRoot = container.attachShadow({ mode: 'open' })
     document.body.appendChild(container)
     
     createRoot(shadowRoot).render(<App />)
     ```

---

## 3. 與 Background / Content Script 通訊

Chrome Extension 的 UI (Popup) 與邏輯層 (Background) 是分離的，需透過 **Message Passing** 溝通。

### 發送訊息 (Popup -> Background)

```typescript
// 在 React Component 中
const handleClick = async () => {
  const response = await chrome.runtime.sendMessage({ type: 'GET_USER_DATA' })
  console.log(response)
}
```

### 接收訊息 (Background / Content)

```typescript
// src/background/index.ts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_USER_DATA') {
    sendResponse({ name: 'User', id: 123 })
  }
})
```

---

## 4. 資料儲存 (Storage)

請勿使用 `localStorage` (會隨 Extension 清除或不同步)，應使用 `chrome.storage.local` 或 `chrome.storage.sync`。

### 建議封裝 Hook (useStorage)

```typescript
// src/hooks/useStorage.ts (範例)
import { useState, useEffect } from 'react'

export function useStorage<T>(key: string, initialValue: T) {
  const [data, setData] = useState<T>(initialValue)

  useEffect(() => {
    chrome.storage.local.get([key], (result) => {
      if (result[key] !== undefined) setData(result[key])
    })
  }, [key])

  const save = (value: T) => {
    chrome.storage.local.set({ [key]: value })
    setData(value)
  }

  return [data, save] as const
}
```

---

## 5. 注意事項 (Best Practices)

1. **CSP (Content Security Policy) 限制**
   - 不使用 `eval()` 或 `new Function()`。
   - 外部資源 (圖片、字型) 需在 `manifest.config.ts` 的 `web_accessible_resources` 宣告，或轉為 Base64。

2. **樣式隔離**
   - Popup 內樣式是獨立的，放心使用。
   - Content Script 注入的 UI **務必**使用 Shadow DOM 或高權重 CSS (如 `!important`)，避免跑版。

3. **非同步操作**
   - Chrome API 多為非同步，建議全面使用 `async/await` 取代 callback hell。
   - `chrome.runtime.onMessage`若要非同步回傳 (sendResponse)，需在監聽器最後回傳 `true`。

4. **Linting**
   - 提交前請執行 `pnpm typecheck` 確保型別正確。
   - 遵循專案內的 `.eslintrc` (若有) 與 Prettier 設定。

---

## 6. 除錯技巧

- **Popup 消失問題**：右鍵點 Extension Icon -> "檢查 (Inspect Popup)"，開啟獨立 DevTools 視窗，即使點擊網頁其他處也不會關閉。
- **Console Log**：
  - Popup 的 log 在 Popup DevTools。
  - Background 的 log 在 Service Worker DevTools。
  - Content Script 的 log 在網頁本身的 DevTools。


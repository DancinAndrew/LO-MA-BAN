# LO-MA-BAN 開發者文件

本專案是使用 **Vite + CRXJS + React + TypeScript** 的 Chrome Extension (Manifest V3) 開發環境。

## 1. 環境需求

- Node.js 22.x
- pnpm 10.x
- Google Chrome (建議最新版)

## 2. 安裝 Node.js 與 pnpm

### Windows

1. 安裝 Node.js 22 LTS：
   - 可使用官方安裝程式，或使用 `nvm-windows`
2. 驗證版本：
   - `node -v`
3. 啟用 Corepack 並使用 pnpm：
   - `corepack enable`
   - `corepack prepare pnpm@10.17.1 --activate`
4. 驗證 pnpm：
   - `pnpm -v`

### macOS

1. 安裝 Node.js 22 LTS：
   - 可使用官方安裝程式，或 `nvm`
2. 驗證版本：
   - `node -v`
3. 啟用 Corepack 並使用 pnpm：
   - `corepack enable`
   - `corepack prepare pnpm@10.17.1 --activate`
4. 驗證 pnpm：
   - `pnpm -v`

## 3. 專案啟動

在專案根目錄執行：

```bash
pnpm install
pnpm dev
```

- `pnpm dev` 會啟動 Vite 開發伺服器，CRXJS 會產生可供 Chrome 載入的開發輸出。

## 4. 建置

```bash
pnpm build
```

- 輸出目錄為 `dist/`。

## 5. 在 Chrome 載入 Extension

1. 開啟 `chrome://extensions`
2. 開啟右上角 **開發人員模式**
3. 點擊 **載入未封裝項目 (Load unpacked)**
4. 選擇本專案的 `dist/` 資料夾

程式碼更新後：
- 若使用開發模式，回到 extension 頁面按重新整理
- 目標網頁也需刷新，確保 content script 更新生效

## 6. 除錯指南

- **Popup**
  - 在 extension 圖示上右鍵，選「檢查 Popup」
- **Service Worker**
  - 到 `chrome://extensions`，在此 extension 卡片內點擊 Service Worker 檢查連結
- **Content Script**
  - 在目標網頁開啟 DevTools (F12)，查看 Console

## 7. 專案結構

```text
src/
  background/index.ts    # Service Worker
  content/index.ts       # Content Script
  popup/
    index.html           # Popup HTML 入口
    main.tsx             # React 入口
    Popup.tsx            # Popup UI
manifest.config.ts       # MV3 設定
vite.config.ts           # Vite + CRXJS 設定
```

## 8. 常用指令

```bash
pnpm dev
pnpm build
pnpm typecheck
```

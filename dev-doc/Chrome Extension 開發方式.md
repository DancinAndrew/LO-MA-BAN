# Chrome Extension 開發方式

:::spoiler 目錄
[TOC]
:::

---

開發 Chrome Extension 其實就像在寫一個具有特殊權限的微型前端應用程式。它主要是由網頁技術（HTML、CSS、JavaScript/TypeScript）構成，但加上了 Chrome 專屬的 API 和一套特定的運行架構。

我們就直接切入核心，來看看你需要掌握的關鍵知識，以及完整的開發生命週期。

---

### 必備知識與核心架構

現在開發 Chrome Extension，首要條件是必須遵循 **Manifest V3 (MV3)** 標準。你需要了解以下幾個核心組件，以及它們如何互相配合：

1. **`manifest.json` (設定檔)：** 這是整個擴充功能的靈魂。它定義了擴充功能的名稱、版本、需要的權限（例如存取特定網站、使用儲存空間），以及指定各個核心腳本的路徑。
2. **Service Worker (Background Script)：** * **作用：** 它是擴充功能的大腦，在瀏覽器背景獨立運行。負責監聽和處理瀏覽器層級的事件（例如：擴充功能安裝、分頁切換、設定鬧鐘定時任務）。
* **限制：** 它**沒有** DOM 存取權限，不能直接操作網頁。


3. **Content Scripts (內容腳本)：**
* **作用：** 這些腳本會被「注入」到使用者正在瀏覽的網頁中。如果你想抓取網頁資料、修改網頁的 DOM（例如在網頁上插入一個按鈕，或改變背景顏色），都要靠它。
* **特點：** 它與原本網頁的 JavaScript 執行環境是隔離的（Isolated World），所以不用擔心變數名稱衝突。


4. **UI 介面 (Popup / Options / Side Panel)：**
* **作用：** 提供使用者操作的介面。Popup 是點擊瀏覽器右上角圖示時彈出的視窗；Options 是擴充功能的設定頁面；Side Panel 則是側邊欄。這些就完全是你熟悉的前端網頁。


5. **Chrome APIs (擴充功能 API)：**
* 需要熟悉幾個常用的 API，例如 `chrome.tabs`（控制分頁）、`chrome.storage`（儲存使用者設定）、`chrome.runtime`（處理安裝事件與通訊）。



---

## 開發與上架的標準流程

了解架構後，你接下來會經歷這樣的開發循環：

**1. 專案初始化與配置 (Setup)**
建立一個新的資料夾，並在裡面建立 `manifest.json`。

* *實務建議：* 如果只是簡單的小工具，原生 JS 就夠了。但如果是中大型專案，建議直接使用現代化的前端工具鏈（例如 Vite + Vue/React/Svelte），並搭配像 `CRXJS` 這樣的套件，它可以幫你處理 MV3 的熱更新 (HMR) 和打包，開發體驗會好很多。

**2. 本地載入與測試 (Load Unpacked)**
打開瀏覽器進入 `chrome://extensions/`，開啟右上角的「開發人員模式」，點擊「載入未封裝項目」，選擇你的專案資料夾（或是打包後的 `dist` 資料夾）。這時候你的 Extension 就會出現在瀏覽器上了。

**3. 開發與跨元件通訊 (Messaging)**
這是開發中最容易卡關的地方。因為 Service Worker、Content Script 和 Popup 運行在不同的環境，它們不能直接呼叫對方的函數或共用變數。
你必須熟練使用 `chrome.runtime.sendMessage` 和 `chrome.runtime.onMessage.addListener` 來互相傳遞訊息（例如：Popup 按下按鈕 -> 發送訊息給 Content Script 去抓網頁資料 -> Content Script 將資料傳回 Popup 顯示）。

**4. 獨立環境除錯 (Debugging)**
Chrome Extension 的除錯需要一點適應期，因為不同組件的 Console (主控台) 是分開的：

* **Popup / Options：** 在該面板上按右鍵點擊「檢查」來開啟獨立的 DevTools。
* **Content Script：** 直接在當下網頁按 F12 打開 DevTools，它的 log 會跟一般網頁的 log 混在一起。
* **Service Worker：** 在 `chrome://extensions/` 頁面中找到你的擴充功能，點擊「Service Worker」連結，會彈出專屬的 DevTools。

**5. 打包與發布 (Publishing)**
開發完成後，將檔案打包成一個 `.zip` 壓縮檔。接著你需要：

* 前往 Chrome Web Store Developer Dashboard。
* 註冊開發者帳號（需繳交一次性費用 $5 USD）。
* 上傳你的 `.zip` 檔，填寫商店圖文介紹、隱私權聲明（非常重要，需詳細說明你索取了哪些權限以及用途）。
* 提交審查。審查時間從幾個小時到幾天不等，通過後就會正式上架。



----

## 測試流程與除錯（Debug）技巧
Chrome 提供了非常完善的**「開發人員模式」（Developer Mode）**，讓你可以在本地端直接載入你的程式碼進行測試，完全不需要經過審核，也不需要打包成 `.crx` 檔案。

以下是完整的測試流程與除錯（Debug）技巧：

---

### 第一步：載入你的插件（Side-loading）

這是最基本且必須的步驟。

1. **開啟擴充功能管理頁面：**
* 在網址列輸入 `chrome://extensions` 並按下 Enter。
* 或者點擊瀏覽器右上角的拼圖圖示 -> 「管理擴充功能」。


2. **開啟開發人員模式：**
* 在頁面右上角，找到**「開發人員模式」**（Developer mode）的開關，將其打開。


3. **載入未封裝項目：**
* 你會看到上方出現一個新的工具列，點擊左側的**「載入未封裝項目」**（Load unpacked）。


4. **選擇資料夾：**
* 選擇你存放 `manifest.json` 檔案的那個**專案根目錄**。



> **注意：** 載入成功後，你就會在列表上看到你的插件，並且可以像正常使用者一樣在瀏覽器上操作它了。

---

### 第二步：開發與更新的循環（重要）

這點是新手最容易卡關的地方。當你修改了程式碼（HTML, CSS, JS）之後，瀏覽器**不會自動更新**插件。

你必須遵循以下步驟：

1. 回到 `chrome://extensions` 頁面。
2. 找到你的插件卡片，點擊右下角的**「重新整理」圖示**（迴轉箭頭）。
3. 如果你的插件有作用於特定網頁（Content Script），請記得到該網頁**重新整理（F5）**，新的程式碼才會生效。

---

### 第三步：如何除錯（Debugging）

Chrome Extension 的架構分為不同部分，每一部分的除錯方式略有不同：

#### 1. 彈出視窗（Popup）的除錯

Popup 視窗一點擊其他地方就會消失，導致很難用一般的 F12 檢查。

* **方法：** 在你的插件圖示上按**右鍵**，選擇**「檢查」**（Inspect Popup）。這會開啟一個獨立的開發者工具視窗，而且不會因為視窗失焦而關閉。

#### 2. 背景服務（Background / Service Worker）的除錯

這是處理邏輯的核心，但它沒有畫面。

* **方法：** 在 `chrome://extensions` 頁面中，你的插件卡片上會有一個 **"Inspect views"**（檢查檢視）的部分，點擊旁邊藍色的 **"Service Worker"** 連結。這會跳出專屬的 Console 視窗。

#### 3. 內容腳本（Content Script）的除錯

這是注入到網頁（如 Google, Facebook）裡的程式碼。

* **方法：** 直接在目標網頁上按 F12 開啟開發者工具，Console 中的 Log 就會顯示在這裡。
* *技巧：* 在 Console 視窗上方有一個下拉選單（預設通常是 `top`），你可以切換到你的 Extension Context 來獨立查看變數。



#### 4. 選項頁面（Options Page）的除錯

* **方法：** 直接在該頁面上按右鍵 -> 「檢查」。

---

### 第四步：自動化測試（進階）

如果你開發的是大型專案，手動點擊測試太慢，可以使用自動化工具：

* **Puppeteer：** Google 官方提供的 Node.js 庫，可以控制 Chrome。你可以設定它在啟動瀏覽器時自動載入你的插件。
* **Jest / Mocha：** 用來測試純 JavaScript 的邏輯函數（Unit Test）。

---

### 常見問題 Check List

如果測試時發現功能沒反應，請檢查：

* **Manifest V3 權限：** 是否在 `manifest.json` 中漏寫了 `permissions` 或 `host_permissions`？
* **錯誤訊息：** `chrome://extensions` 頁面上的插件卡片如果出現紅色的 **"Errors"** 按鈕，點進去可以看到詳細的報錯堆疊（Stack trace）。
* **Console.log：** 善用 `console.log`，但要確認你是在哪一個環境（Popup, Background, 或是網頁本身）查看 Log。


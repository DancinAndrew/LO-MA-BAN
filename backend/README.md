# ScoutNet Backend — 兒童網路安全網址分析 API

針對 18 歲以下使用者設計的網址安全與內容適齡分析 API。整合**釣魚/資安偵測**與 **Exa AI 內容適齡檢查**，提供 RESTful API 供前端（Chrome Extension）呼叫。

## API 端點總覽

| Method | Path | 說明 |
|--------|------|------|
| `POST` | `/api/v1/scan` | 第一階段：資安 + 內容適齡分析 → 兒童友善報告 |
| `POST` | `/api/v1/scan/persuade` | 第二階段：使用者理由勸阻 + 教育 |
| `GET`  | `/health` | 伺服器健康檢查 |

---

## 快速啟動

```bash
cd backend

# 使用 uv（推薦）
uv sync
cp .env.example .env   # 填入 API 金鑰
uv run python main.py

# 或使用 pip
pip install fastapi uvicorn httpx openai python-dotenv pydantic-settings
python main.py
```

啟動後：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

---

## 前端整合指南（Chrome Extension）

Extension 端**不持有任何 API Key**，所有安全檢查和 AI 分析都由後端代理完成。

### 基本架構

```
Chrome Extension (popup / content script / background)
  → fetch() / chrome.runtime.sendMessage()
    → POST http://localhost:8000/api/v1/scan
    ← JSON response（含 report 給 UI 渲染）
```

### 第一階段：掃描網址

```typescript
const BASE_URL = "http://localhost:8000";

async function scanUrl(url: string) {
  const resp = await fetch(`${BASE_URL}/api/v1/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return await resp.json();
}

// 使用範例
const result = await scanUrl("https://example.com");

// 關鍵欄位
result.risk_source;       // "phishing" | "content" | "none"
result.final_risk_level;  // "critical" | "high" | "medium" | "low"
result.report;            // 兒童友善報告（給 UI 渲染）
```

### 第二階段：使用者堅持要進入時的勸阻

當使用者在第一階段看到警告後仍輸入理由想繼續時，呼叫第二階段：

```typescript
async function persuadeUser(userInput: string, firstStageReport: object) {
  const resp = await fetch(`${BASE_URL}/api/v1/scan/persuade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_input: userInput,
      first_stage_report: firstStageReport,
    }),
  });

  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return await resp.json();
}

// 使用範例：將第一階段的 report 原封不動傳回
const stage2 = await persuadeUser(
  "我只是好奇想看看...",
  result.report   // 第一階段拿到的 report 物件
);

stage2.second_stage_result.reason_analysis.is_reasonable;  // false
stage2.second_stage_result.encouraging_message;            // 鼓勵訊息
```

### 在 Background Script 中封裝

建議在 `background/index.ts` 統一封裝 API 呼叫，popup 和 content script 透過 `chrome.runtime.sendMessage()` 取得結果：

```typescript
// background/index.ts
const API_BASE = "http://localhost:8000";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "SCAN_URL") {
    fetch(`${API_BASE}/api/v1/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: message.url }),
    })
      .then((r) => r.json())
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // keep message channel open for async response
  }

  if (message.type === "PERSUADE") {
    fetch(`${API_BASE}/api/v1/scan/persuade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_input: message.userInput,
        first_stage_report: message.report,
      }),
    })
      .then((r) => r.json())
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

// popup 或 content script 呼叫方式
const resp = await chrome.runtime.sendMessage({
  type: "SCAN_URL",
  url: "https://example.com",
});
if (resp.success) {
  const report = resp.data.report;
  // 渲染 UI ...
}
```

### 前端 UI 渲染重點欄位

`report` 物件中各區塊對應前端 UI 元件：

| report 欄位 | UI 用途 | 資料結構 |
|-------------|---------|----------|
| `report_metadata.risk` | 頂部風險標籤（icon + color + label） | `{ level, score, icon, color, label }` |
| `kid_friendly_summary` | 主要風險摘要卡片 | `{ title, simple_message, short_explanation, action_verb }` |
| `evidence_cards` | 證據卡片輪播 | `[{ id, icon, title, content, severity }]` |
| `pattern_analysis` | 網址結構視覺化拆解 | `{ tld_analysis, domain_structure, visual_summary }` |
| `interactive_quiz` | 互動選擇題 | `{ question, options[], correct_answer_id }` |
| `safety_tips` | 安全小撇步列表 | `[{ icon, tip, why }]` |
| `next_steps` | 建議行動按鈕 | `[{ action, priority, icon, link? }]` |
| `raw_analysis` | LLM 原始分析（可展開的進階資訊） | 完整 LLM JSON 回應 |

**釣魚場景特有欄位**（在 `raw_analysis` 中）：

| 欄位 | 說明 |
|------|------|
| `likely_intended_urls` | 推測使用者想去的正確網址（如 `["paypal.com"]`） |
| `alternative_recommendations` | 同類替代網站（如 `[{name: "蝦皮", url: "https://shopee.tw"}]`） |

### 錯誤處理

所有錯誤回應都包含 `request_id` 方便追蹤：

```typescript
try {
  const result = await scanUrl(url);
  // 正常處理 ...
} catch (err) {
  // HTTP 422 — URL 格式錯誤（缺少 scheme 等）
  // HTTP 502 — 所有 Security API 皆失敗
  // HTTP 500 — 伺服器內部錯誤
}
```

422 回應範例：

```json
{
  "detail": "請求參數驗證失敗",
  "errors": [
    {
      "type": "value_error",
      "loc": ["body", "url"],
      "msg": "Input should be a valid URL",
      "input": "not-a-url"
    }
  ],
  "request_id": "a1b2c3d4e5f6"
}
```

### 逾時建議

| 端點 | 建議 timeout | 說明 |
|------|-------------|------|
| `/api/v1/scan` | **120–180 秒** | 含 4 個 Security API 並行查詢 + LLM 分析 |
| `/api/v1/scan/persuade` | **60–90 秒** | 僅 LLM 分析 |
| `/health` | **5 秒** | 簡單 health check |

---

## API 詳細參考

### `GET /health`

```json
{ "status": "ok", "version": "2.0.0" }
```

---

### `POST /api/v1/scan`

#### Request

| 欄位 | 型別 | 必填 | 說明 |
|------|------|:----:|------|
| `url` | string (URL) | **是** | 目標網址，須含 scheme（`https://`） |
| `quick_scan` | boolean | 否 | 僅跑安全檢查，跳過 LLM 深度分析（預設 `false`） |
| `force_deep_analysis` | boolean | 否 | 即使風險低也強制跑 LLM 深度分析（預設 `false`） |

```json
{
  "url": "https://example.com",
  "quick_scan": false,
  "force_deep_analysis": false
}
```

#### Response

| 欄位 | 型別 | 說明 |
|------|------|------|
| `target_url` | string | 分析的目標 URL |
| `risk_source` | string | `"phishing"` / `"content"` / `"none"` — 風險來源 |
| `security_check` | object | 安全檢查彙總（4 個 API 並行結果） |
| `llm_analysis` | object \| null | LLM 深度分析結果 |
| `content_classification` | object \| null | 內容適齡分類（僅路徑 B） |
| `report` | object \| null | **兒童友善報告（前端渲染用）** |
| `final_risk_level` | string | 最終風險等級 |
| `timestamp` | string | ISO 8601 UTC 時間戳 |

#### 分流邏輯

```
URL → 安全平台並行檢查（VT / URLhaus / PhishTank / Google SB）
       │
       ├─ 有風險 → 路徑 A：Featherless AI 釣魚分析
       │           （含預測正確網址 + 推薦替代）
       │           → risk_source = "phishing"
       │
       └─ 無風險 → Exa AI 取得內容 → Featherless 判斷適齡性
                    ├─ 不適合 → 路徑 B：Featherless AI 內容風險分析
                    │           → risk_source = "content"
                    └─ 適合   → 低風險簡要報告
                                → risk_source = "none"
```

#### `report` 完整結構

```json
{
  "report_metadata": {
    "target_url": "https://...",
    "target_domain": "example.com",
    "target_tld": "com",
    "timestamp": "2026-02-28T...",
    "risk": {
      "level": "critical",
      "score": 100,
      "icon": "🔴",
      "color": "#ef4444",
      "label": "超級危險"
    },
    "confidence": {
      "level": "high",
      "icon": "✅",
      "label": "很確定"
    }
  },
  "kid_friendly_summary": {
    "title": "🔴 超級危險！",
    "simple_message": "🚨 這個網站很可能是騙人的，千萬不要點進去！",
    "short_explanation": "...",
    "emoji_reaction": "🔴",
    "action_verb": "不要點"
  },
  "evidence_cards": [
    {
      "id": "evidence_1",
      "icon": "🚨",
      "title": "🚨 偵測到威脅",
      "content": "VirusTotal: 惡意:5 可疑:2",
      "severity": "high",
      "expandable": true
    }
  ],
  "pattern_analysis": {
    "tld_analysis": { "tld": "cfd", "is_common": false, "is_high_risk": true, "kid_message": "..." },
    "domain_structure": { "length": 59, "has_numbers": true, "has_hyphens": true, "kid_message": "..." },
    "visual_summary": {
      "url_parts": [
        { "part": "https://", "label": "協定", "safe": true },
        { "part": "example.cfd", "label": "域名", "safe": false },
        { "part": "/path", "label": "路徑", "safe": true }
      ]
    }
  },
  "interactive_quiz": {
    "enabled": true,
    "question": "🔍 你覺得這個網址哪裡怪怪的？",
    "hint": "仔細看每個字母喔！",
    "type": "single_choice",
    "options": [
      { "id": "A", "text": "...", "is_correct": false, "explanation": "...", "feedback_icon": "❌" },
      { "id": "B", "text": "...", "is_correct": true,  "explanation": "...", "feedback_icon": "✅" }
    ],
    "correct_answer_id": "B",
    "learning_point": "...",
    "difficulty": "easy"
  },
  "safety_tips": [
    { "id": "tip_1", "icon": "🔍", "tip": "不隨便點陌生連結", "why": "...", "action_text": "記住囉！" }
  ],
  "next_steps": [
    { "action": "❌ 不要點擊此連結", "priority": "high", "icon": "🚫" },
    { "action": "🔍 用 VirusTotal 再檢查一次", "priority": "medium", "icon": "🔎", "link": "https://www.virustotal.com" }
  ],
  "raw_analysis": { "...LLM 完整回應..." }
}
```

#### 錯誤回應

| Status | 說明 |
|--------|------|
| `422` | Request body 驗證失敗（缺少 `url`、格式錯誤等） |
| `502` | 所有 Security API 呼叫失敗 |

---

### `POST /api/v1/scan/persuade`

#### Request

| 欄位 | 型別 | 必填 | 說明 |
|------|------|:----:|------|
| `user_input` | string | **是** | 使用者解釋為什麼仍想進入（min 1 字） |
| `first_stage_report` | ReportResponse | **是** | 第一階段回應中的 `report` 物件原封不動傳回 |

```json
{
  "user_input": "我只是好奇想看看...",
  "first_stage_report": { "report_metadata": { ... }, ... }
}
```

#### Response

```json
{
  "user_input": "我只是好奇想看看...",
  "first_stage_report_summary": {
    "target_url": "https://...",
    "risk_level": "critical",
    "risk_label": "超級危險",
    "risk_score": 100,
    "risk_source": "phishing"
  },
  "second_stage_result": {
    "behavior_consequence_warning": "如果你真的點開這個連結，可能會...",
    "reason_analysis": {
      "is_reasonable": false,
      "analysis": "我知道你很想知道...",
      "empathy_note": "我理解你的心情，但是..."
    },
    "general_warnings": ["永遠不要輸入個人資訊...", "..."],
    "recommended_actions": ["和爸爸媽媽一起確認...", "..."],
    "encouraging_message": "你做得很好，能夠意識到這個連結有風險..."
  }
}
```

#### 前端使用 `second_stage_result` 的方式

| 欄位 | UI 用途 |
|------|---------|
| `behavior_consequence_warning` | 行為後果警告卡片（紅色底色） |
| `reason_analysis.empathy_note` | 同理心對話框（藍色底色） |
| `reason_analysis.is_reasonable` | 控制是否顯示「仍要前往」按鈕 |
| `general_warnings` | 警告列表 |
| `recommended_actions` | 建議行動按鈕 |
| `encouraging_message` | 底部鼓勵訊息 |

---

## 專案結構

```
backend/
├── main.py                          # FastAPI 入口 + lifespan + middleware 註冊
├── config.py                        # pydantic-settings 集中設定（Settings class）
├── dependencies.py                  # FastAPI DI providers（方便測試時 override）
├── middleware.py                    # Request-ID middleware + log filter
├── exceptions.py                   # 統一例外處理（含 request_id）
├── pyproject.toml                   # uv 依賴管理
├── routers/
│   ├── scan.py                      # POST /api/v1/scan
│   └── persuade.py                  # POST /api/v1/scan/persuade
├── schemas/
│   ├── requests.py                  # ScanRequest, PersuasionRequest
│   └── responses.py                 # ScanResponse, PersuasionResponse, ReportResponse, ...
├── services/
│   ├── security_checker.py          # async 並行 4 API 安全檢查
│   ├── threat_analysis.py           # Featherless AI 深度分析（釣魚 + 內容風險）
│   ├── content_checker.py           # Exa AI 內容取得 + 適齡分類
│   ├── scan_orchestrator.py         # 第一階段掃描流程編排
│   ├── report_generator.py          # 兒童友善報告生成
│   ├── quiz_generator.py            # 互動問答生成
│   └── persuasion.py                # 第二階段勸阻分析
├── tests/
│   ├── test_api.py                  # 端對端測試腳本
│   └── output/                      # 測試輸出結果
├── examples/                        # 範例輸出
│   ├── first_stage/{phishing,violence,porn}/
│   └── second_stage/{phishing,violence,porn}/
├── .env.example
└── .gitignore
```

---

## 環境變數 (.env)

完整範本見 `.env.example`。

### Featherless AI（必填）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `FEATHERLESS_API_KEY` | — | **必填**，Featherless AI 金鑰 |
| `FEATHERLESS_BASE_URL` | `https://api.featherless.ai/v1` | OpenAI-compatible base URL |
| `FEATHERLESS_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | 模型名稱 |
| `FEATHERLESS_TEMPERATURE` | `0.1` | 生成溫度 |
| `FEATHERLESS_MAX_TOKENS` | `2000` | 最大 token 數 |
| `FEATHERLESS_TOP_P` | `0.9` | Top-P 取樣 |

### LLM 任務級覆寫

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `CONTENT_CLASSIFY_TEMPERATURE` | `0.1` | 內容分類溫度 |
| `CONTENT_CLASSIFY_MAX_TOKENS` | `400` | 內容分類最大 tokens |
| `PERSUASION_TEMPERATURE` | `0.1` | 勸阻分析溫度 |
| `PERSUASION_MAX_TOKENS` | `1000` | 勸阻分析最大 tokens |

### Exa AI（內容適齡檢查）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `EXA_API_KEY` | — | **建議**，未設定則跳過內容適齡分析 |
| `EXA_BASE_URL` | `https://api.exa.ai` | Exa API base URL |
| `EXA_TIMEOUT` | `60` | 請求逾時秒數 |
| `EXA_MAX_AGE_HOURS` | `24` | 快取最大時效 |
| `EXA_LIVECRAWL_TIMEOUT_MS` | `25000` | Live crawl 逾時毫秒 |
| `EXA_SEARCH_NUM_RESULTS` | `5` | 搜尋回傳筆數 |

### Security API

| 變數 | 說明 |
|------|------|
| `VIRUSTOTAL_API_KEY` | 選填，VirusTotal API v3 |
| `VIRUSTOTAL_BASE_URL` | 預設 `https://www.virustotal.com/api/v3` |
| `URLHAUS_AUTH_KEY` | 選填，URLhaus |
| `URLHAUS_BASE_URL` | 預設 `https://urlhaus-api.abuse.ch/v1` |
| `PHISHTANK_API_KEY` | 選填，PhishTank |
| `PHISHTANK_BASE_URL` | 預設 `https://api.phishtank.com/v2/phishtank` |
| `GOOGLE_SAFE_BROWSING_API_KEY` | 建議，Google Safe Browsing v4 |
| `GOOGLE_SAFE_BROWSING_BASE_URL` | 預設 `https://safebrowsing.googleapis.com/v4` |

> Security API Key 皆為可選。缺少的來源會自動跳過，不影響其他來源運作。但至少需要一組才能產生有意義的安全檢查結果。

### 其他

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `CONTENT_MAX_CHARS` | `8000` | 內容分析截斷字數上限 |
| `API_TIMEOUT` | `30` | 外部 API 呼叫逾時秒數 |
| `HOST` | `0.0.0.0` | 監聽地址 |
| `PORT` | `8000` | 監聽 port |
| `APP_TITLE` | `ScoutNet API` | Swagger 標題 |
| `APP_VERSION` | `2.0.0` | API 版本 |
| `USER_AGENT` | `ScamAnalyzer/2.0` | 外部 API 呼叫用 User-Agent |
| `CORS_ORIGINS` | `["*"]` | CORS 允許來源（JSON array 或逗號分隔） |

---

## 部署 API（Deploy）

### Railway

1. **建立專案**：到 [Railway](https://railway.app) 建立新專案，選擇 **Deploy from GitHub repo**，選取本專案。
2. **設定 Root Directory**：在專案 Settings → **Root Directory** 設為 `backend`（讓 build 與 start 都在 `backend/` 下執行）。
3. **Build**：Railway 會依 `requirements.txt` 執行 `pip install -r requirements.txt`（或 Nixpacks 偵測 Python 後安裝依賴）。
4. **Start Command**（若未自動偵測 Procfile）：  
   `uvicorn main:app --host 0.0.0.0 --port $PORT`  
   （`Procfile` 已寫好則可省略此步。）
5. **環境變數**：在 Railway 專案 → **Variables** 新增 `.env` 中需要的變數，至少：
   - `FEATHERLESS_API_KEY`（必填）
   - `EXA_API_KEY`（內容適齡需要）
   - 其餘 Security API 金鑰依需求新增。
6. **部署完成**：Railway 會給一個公開 URL（如 `https://xxx.up.railway.app`）。  
   - Health check：`GET https://你的網址/health`  
   - 分析 API：`POST https://你的網址/api/v1/analyze`，body `{ "url": "https://example.com" }`。
7. **前端串接**：在 extension 的 `src/siteDetection.ts` 將 `ANALYZE_API_URL` 改為你的 Railway URL + `/api/v1/analyze`，並在 `manifest.config.ts` 的 `host_permissions` 加入該網域。

### 其他平台（Render / Fly.io / 自建主機）

- **Render**：選 Python Web Service，Root Directory 設 `backend`，Build Command：`pip install -r requirements.txt`，Start Command：`uvicorn main:app --host 0.0.0.0 --port $PORT`。
- **Fly.io**：可加一個 `Dockerfile` 用 `python:3.12-slim` + `pip install -r requirements.txt` + `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`，並在 `fly.toml` 設定 `internal_port = 8000` 與 env。
- **自建**：`pip install -r requirements.txt` 後執行 `uvicorn main:app --host 0.0.0.0 --port 8000`，或用 Gunicorn：`gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000`。

---

## 技術特點

- **全 async**：`security_checker` 使用 `httpx` + `asyncio.gather` 並行呼叫 4 API
- **OpenAI SDK**：LLM 呼叫使用 `openai.AsyncOpenAI`（Featherless 相容）
- **pydantic-settings**：`config.py` 使用 `BaseSettings` 管理所有環境變數，支援型別驗證與預設值
- **FastAPI DI**：`dependencies.py` 統一管理服務注入，方便測試時 override
- **Request-ID**：`middleware.py` 自動為每個請求生成 `X-Request-ID`，貫穿 log 與錯誤回應
- **統一錯誤處理**：`exceptions.py` 攔截 HTTP / 驗證 / 未處理例外，回應格式一致
- **Orchestrator 模式**：`scan_orchestrator.py` 編排第一階段完整流程（安全檢查 → 分流 → LLM → 報告）
- **兒童輔導員 persona**：所有 AI 分析以「18 歲以下兒童輔導員」角色回應
- **釣魚預測**：自動推測使用者可能想去的正確網址 + 推薦替代網站
- **LLM fallback**：LLM API 失敗時自動降級（`fallback_mode: true`），不會讓整個 request 失敗
- **Stateless**：不存任何狀態，不寫檔案。前端帶完整 context，後端單純做 API proxy + orchestration
- **CORS 可配置**：透過 `CORS_ORIGINS` 環境變數控制，正式上線前建議限縮

---

## 端對端測試

```bash
# 1. 啟動 server
cd backend && uv run python main.py

# 2. 在另一個 terminal 執行測試（涵蓋 phishing / violence / porn 三種場景）
cd backend && uv run python tests/test_api.py
```

測試結果會存放在 `tests/output/` 中。

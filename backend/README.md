# ScoutNet Backend

ScoutNet Chrome Extension 的後端 API Server。負責安全威脅情報查詢與 AI 深度分析的 orchestration，Extension 端不持有任何 API Key。

## Tech Stack

| 類別 | 工具 |
|------|------|
| Web Framework | FastAPI |
| ASGI Server | uvicorn |
| HTTP Client | httpx (async) |
| LLM SDK | openai (AsyncOpenAI, Featherless/Qwen compatible) |
| Package Manager | uv |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)

## Quick Start

```bash
# 1. 安裝依賴
cd backend
uv sync

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入各平台 API Key

# 3. 啟動開發伺服器 (hot-reload，HOST/PORT 讀自 .env 或 config 預設)
uv run python main.py
```

Server 啟動後（預設 port 為 `.env` 的 `PORT`，未設則 8000）：
- API: `http://localhost:8000`
- **Swagger UI** (`http://localhost:8000/docs`) — 互動式 API 文件，可在此頁面直接發送請求、查看 request/response 結構，適合除錯與手動測試。
- **ReDoc** (`http://localhost:8000/redoc`) — 以閱讀為主的 API 文件（三欄式排版），適合查閱端點說明與 schema，不提供「Try it out」。

## Environment Variables

所有設定透過 `.env` 管理，參考 `.env.example`：

| 變數 | 必填 | 說明 |
|------|:----:|------|
| `FEATHERLESS_API_KEY` | **是** | Featherless AI API Key |
| `FEATHERLESS_BASE_URL` | 否 | OpenAI-compatible base URL，預設 `https://api.featherless.ai/v1` |
| `FEATHERLESS_MODEL` | 否 | 模型名稱，預設 `Qwen/Qwen2.5-7B-Instruct` |
| `FEATHERLESS_TEMPERATURE` | 否 | 生成溫度，預設 `0.1` |
| `FEATHERLESS_MAX_TOKENS` | 否 | 最大 token 數，預設 `2000` |
| `VIRUSTOTAL_API_KEY` | 否 | VirusTotal API v3 Key（無則跳過該來源） |
| `URLHAUS_AUTH_KEY` | 否 | URLhaus Auth Key（無則跳過） |
| `PHISHTANK_API_KEY` | 否 | PhishTank API Key（目前免費版不需要） |
| `GOOGLE_SAFE_BROWSING_API_KEY` | 否 | Google Safe Browsing API v4 Key（無則跳過） |
| `HOST` | 否 | 監聽地址，預設 `0.0.0.0` |
| `PORT` | 否 | 監聽 port，預設 `8000` |
| `API_TIMEOUT` | 否 | 外部 API 呼叫逾時秒數，預設 `30` |

> Security API Key 皆為可選。缺少的來源會自動跳過，不影響其他來源運作。但至少需要一組才能產生有意義的安全檢查結果。

## Project Structure

```
backend/
├── main.py                     # FastAPI app entry + uvicorn
├── config.py                   # 環境變數集中管理
├── pyproject.toml              # uv 專案設定 + 依賴宣告
├── uv.lock                     # uv lock file（應 commit）
├── .env.example                # 環境變數範本
├── routers/
│   └── analyze.py              # POST /api/v1/analyze
├── schemas/
│   ├── requests.py             # Request models (Pydantic v2)
│   └── responses.py            # Response models (Pydantic v2)
└── services/
    ├── security_checker.py     # 4 源威脅情報並行查詢
    ├── llm_analyzer.py         # Featherless/Qwen LLM 深度分析
    └── report_generator.py     # 兒童友善 JSON 報告產生器
```

---

## API Reference

### `GET /health`

Health check，用於部署平台存活探測。

**Response** `200`

```json
{
  "status": "ok",
  "version": "2.0.0"
}
```

---

### `POST /api/v1/analyze`

主要端點。接收一個 URL，依序執行：
1. **Security Check** — 並行查詢 VirusTotal、URLhaus、PhishTank、Google Safe Browsing
2. **LLM Analysis** — 當風險為 critical/high/medium 時，將安全檢查結果送給 Featherless AI 做深度分析
3. **Report Generation** — 產生兒童友善的教學報告（含互動選擇題）

#### Request

```
Content-Type: application/json
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|:----:|------|
| `url` | string (URL) | **是** | 要分析的目標網址，須含 scheme (`https://`) |

**Request 範例：**

```json
{
  "url": "https://example.com"
}
```

#### Response `200`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `target_url` | string | 分析的目標 URL |
| `security_check` | object | 安全檢查彙總結果 |
| `llm_analysis` | object \| null | LLM 深度分析結果（僅當 overall_risk 為 critical/high/medium 時有值） |
| `report` | object | 兒童友善教學報告 |
| `final_risk_level` | string | 最終風險等級 |
| `timestamp` | string | ISO 8601 UTC 時間戳 |

**`security_check` 結構：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `overall_risk` | string | `"critical"` / `"high"` / `"medium"` / `"low"` / `"inconclusive"` |
| `confidence` | string | `"high"` / `"medium"` / `"low"` |
| `risk_score` | integer | 0–100 綜合風險分數 |
| `checked_sources` | integer | 實際查詢成功的來源數量 |
| `critical_flags` | array | 被標記為 critical 的來源詳情 |
| `warnings` | array | 被標記為 warning/caution 的來源詳情 |
| `raw_results` | array | 各來源的原始回傳結果 |
| `target_url` | string | 查詢的目標 URL |
| `timestamp` | string | 查詢時間 |

**`llm_analysis` 結構（LLM 輸出，semi-structured）：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `risk_level` | string | LLM 判斷的風險等級 |
| `confidence` | string | LLM 對判斷的信心 |
| `risk_score` | integer | 0–100 |
| `threat_summary` | string | 一句話威脅摘要 |
| `evidence_analysis` | array\<string\> | 逐條證據分析 |
| `why_unsafe` | string | 詳細解釋為何不安全（200–300 字） |
| `technical_details` | object | `detected_by`, `threat_types`, `indicators` |
| `user_warnings` | array\<string\> | 給使用者的警告 |
| `recommendations` | array\<string\> | 建議行動 |
| `uncertainties` | array\<string\> | 不確定因素 |
| `quiz` | object | 互動教學選擇題（LLM 生成） |
| `fallback_mode` | boolean | `true` 表示 LLM 呼叫失敗，使用降級結果 |
| `llm_metadata` | object | `model`, `usage`（token 用量） |

> `llm_analysis` 的欄位由 LLM 動態產生，上表為預期欄位但不保證每個都存在。前端應使用 optional chaining 處理。

**`report` 結構：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `report_metadata` | object | URL、域名、TLD、風險 UI 資訊（icon/color/label） |
| `kid_friendly_summary` | object | 兒童版風險摘要（title, simple_message, action_verb） |
| `evidence_cards` | array | 前端可輪播的證據卡片 |
| `pattern_analysis` | object | 域名結構分析（TLD 風險、域名長度、視覺化拆解） |
| `interactive_quiz` | object | 互動選擇題（LLM 生成或 fallback） |
| `safety_tips` | array | 安全小撇步卡片 |
| `next_steps` | array | 建議行動列表 |

#### Error Responses

| Status | 說明 |
|--------|------|
| `422` | Request body 驗證失敗（缺少 `url`、格式錯誤等），FastAPI 自動回傳 validation error |
| `502` | 所有 Security API 呼叫失敗 |

**422 範例：**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "url"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

---

## Architecture Notes

### Request Flow

```
Chrome Extension
  → POST /api/v1/analyze { url }
    → SecurityCheckerService.check_all()
        → asyncio.gather(VirusTotal, URLhaus, PhishTank, Google SB)  ← 並行
    → LLMAnalyzerService.analyze()
        → openai AsyncOpenAI (Featherless endpoint)
    → ReportGeneratorService.generate()
        → 純 dict 組裝，無 file I/O
  ← JSON response
```

### Key Design Decisions

- **Security API 並行查詢**：四個威脅情報 API 透過 `asyncio.gather` 同時呼叫，而非依序等待。延遲取決於最慢的那個 API，而非四者之和。
- **openai SDK + base_url**：Featherless 提供 OpenAI-compatible endpoint，直接使用 `openai.AsyncOpenAI(base_url=...)` 呼叫，不需要手動組 HTTP request。
- **LLM fallback**：當 LLM API 呼叫失敗時，自動使用 `_fallback()` 產生降級結果（`fallback_mode: true`），不會讓整個 request 失敗。
- **Stateless**：不存任何狀態，不寫檔案。前端帶完整 context，後端單純做 API proxy + orchestration。
- **CORS 全開**：MVP 階段 `allow_origins=["*"]`，部署時應限縮為 Extension 的 origin。

### Adding a New Security Source

1. 在 `services/security_checker.py` 新增 `async _check_xxx()` method
2. 在 `check_all()` 的 `asyncio.gather` 中加入新的呼叫
3. 回傳格式需包含 `source`, `available`, `found` 欄位，可選 `risk_level`
4. `_aggregate()` 會自動處理新來源的風險計算

### Changing the LLM Model

修改 `.env` 中的 `FEATHERLESS_MODEL` 即可切換模型。只要該模型支援 OpenAI-compatible chat completions API 且支援 `response_format: { type: "json_object" }`，即可直接使用。

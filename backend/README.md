# ScoutNet Backend — 兒童網路安全網址分析 API

針對 18 歲以下使用者設計的網址安全與內容適齡分析 API。整合**釣魚/資安偵測**與 **Exa AI 內容適齡檢查**，提供 RESTful API 供前端呼叫。

## API 端點

| Method | Path | 說明 |
|--------|------|------|
| `POST` | `/api/v1/analyze` | 第一階段：資安 + 內容適齡分析 → 兒童友善報告 |
| `POST` | `/api/v1/second-stage/analyze` | 第二階段：使用者理由勸阻 + 教育 |
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
pip install fastapi uvicorn httpx openai python-dotenv
python main.py
```

啟動後：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

---

## 第一階段 `POST /api/v1/analyze`

### Request

```json
{
  "url": "https://example.com",
  "skip_llm": false,
  "force_llm": false
}
```

### Response

```json
{
  "target_url": "https://example.com",
  "risk_source": "phishing | content | none",
  "final_risk_level": "critical | high | medium | low",
  "timestamp": "...",
  "security_check": { "overall_risk": "...", ... },
  "llm_analysis": { ... },
  "content_classification": { ... },
  "report": {
    "report_metadata": { ... },
    "kid_friendly_summary": { ... },
    "evidence_cards": [ ... ],
    "pattern_analysis": { ... },
    "interactive_quiz": { ... },
    "safety_tips": [ ... ],
    "next_steps": [ ... ],
    "raw_analysis": { ... }
  }
}
```

### 分流邏輯

```
URL → 安全平台並行檢查（VT/URLhaus/PhishTank/Google SB）
       │
       ├─ 有風險 → 路徑 A：Featherless AI 釣魚分析（含預測正確網址 + 推薦替代）
       │
       └─ 無風險 → Exa AI 取得內容 → Featherless 判斷適齡性
                    ├─ 不適合 → 路徑 B：Featherless AI 內容風險分析
                    └─ 適合   → 低風險簡要報告
```

---

## 第二階段 `POST /api/v1/second-stage/analyze`

### Request

```json
{
  "user_input": "我只是好奇想看看...",
  "first_stage_report": { "report_metadata": { ... }, ... }
}
```

### Response

```json
{
  "user_input": "...",
  "first_stage_report_summary": { "target_url": "...", "risk_level": "..." },
  "second_stage_result": {
    "behavior_consequence_warning": "...",
    "reason_analysis": { "is_reasonable": false, "analysis": "...", "empathy_note": "..." },
    "general_warnings": ["..."],
    "recommended_actions": ["..."],
    "encouraging_message": "..."
  }
}
```

---

## 專案結構

```
backend/
├── main.py                          # FastAPI 入口
├── config.py                        # 環境變數 / API 金鑰
├── pyproject.toml                   # uv 依賴管理
├── routers/
│   ├── analyze.py                   # POST /api/v1/analyze（分流邏輯）
│   └── second_stage.py              # POST /api/v1/second-stage/analyze
├── schemas/
│   ├── requests.py                  # AnalyzeRequest, SecondStageRequest
│   └── responses.py                 # AnalyzeResponse, SecondStageResponse, ...
├── services/
│   ├── security_checker.py          # async 並行 4 API 安全檢查
│   ├── llm_analyzer.py              # Featherless AI（釣魚 + 內容風險）
│   ├── content_checker.py           # Exa AI 內容取得 + 適齡分類
│   ├── report_generator.py          # 兒童友善報告生成
│   └── second_stage_analyzer.py     # 第二階段勸阻分析
├── examples/                        # 範例輸出
│   ├── first_stage/{phishing,violence,porn}/
│   └── second_stage/{phishing,violence,porn}/
├── .env.example
└── .gitignore
```

---

## 環境變數 (.env)

| 變數 | 必填 | 說明 |
|------|------|------|
| `FEATHERLESS_API_KEY` | ✅ | Featherless AI 金鑰 |
| `EXA_API_KEY` | ✅* | Exa AI 金鑰（內容適齡檢查） |
| `GOOGLE_SAFE_BROWSING_API_KEY` | 建議 | Google Safe Browsing v4 |
| `VIRUSTOTAL_API_KEY` | 選填 | VirusTotal API v3 |
| `URLHAUS_AUTH_KEY` | 選填 | URLhaus |
| `PHISHTANK_API_KEY` | 選填 | PhishTank |

\* 未設定 `EXA_API_KEY` 時，僅保留資安檢查結果，無法做內容適齡分析。

---

## 技術特點

- **全 async**：security_checker 使用 `httpx` + `asyncio.gather` 並行呼叫 4 API
- **OpenAI SDK**：LLM 呼叫使用 `openai.AsyncOpenAI`（Featherless 相容）
- **分層架構**：`routers/` → `services/` → `schemas/`，符合 FastAPI 最佳實踐
- **兒童輔導員 persona**：所有 AI 分析以「18 歲以下兒童輔導員」角色回應
- **釣魚預測**：自動推測使用者可能想去的正確網址 + 推薦替代網站
- **CORS 已開啟**：正式上線前建議限縮 `allow_origins`

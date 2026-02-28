# LO_MA_BAN Backend — 兒童網路安全網址分析

針對 18 歲以下使用者設計的網址安全與內容適齡分析後端。整合**釣魚/資安偵測**與**內容適齡檢查**，提供兩個獨立 API：

| API | 說明 |
|-----|------|
| **第一階段** (`first_stage`) | 輸入 URL → 資安檢查 + 內容適齡分析 → 兒童友善報告 |
| **第二階段** (`second_stage`) | 輸入使用者理由 + 第一階段報告 → 勸阻與教育分析 |

---

## 流程架構

```
                      ┌──────────────────────┐
                      │    第一階段 API        │
                      │   first_stage.main    │
                      └──────────────────────┘
                                │
                      輸入 URL  │
                                ▼
              ┌─────────────────────────────────────┐
              │ Step 1: 安全平台 API 檢查            │
              │ (VirusTotal / URLhaus / PhishTank /  │
              │  Google Safe Browsing)               │
              └─────────────────────────────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          │ 有風險                                     │ 無明顯風險
          ▼                                            ▼
    【路徑 A】                               ┌──────────────────┐
    標註釣魚／資安風險                         │ Exa 取得網頁內容  │
    → Featherless AI 分析                     │（失敗→搜尋討論）  │
    → 預測正確網址 + 推薦替代                  └──────────────────┘
    → 03_final_report                                  │
                                         ┌─────────────┴──────────────┐
                                         │ 不當內容                    │ 適合兒童
                                         ▼                            ▼
                                   【路徑 B】                    【低風險】
                                   內容適齡分析                   簡要報告
                                   → 03_final_report

        ════════════════════════════════════════════

                      ┌──────────────────────┐
                      │    第二階段 API        │
                      │  second_stage.analyzer│
                      └──────────────────────┘
                                │
              使用者理由 + 第一階段報告
                                │
                                ▼
              ┌─────────────────────────────────────┐
              │ Featherless AI 分析                  │
              │ → 行為後果警告 / 理由分析 / 建議     │
              └─────────────────────────────────────┘
                                │
                                ▼
                  second_stage_result.json + .md
```

---

## 專案結構

```
backend/
├── shared/                          # 共用模組
│   ├── config.py                    # .env 讀取、API 金鑰、設定
│   └── utils.py                     # save_json、load_json、step_marker
│
├── first_stage/                     # API 1：網址分析
│   ├── main.py                      # 入口：資安 → 內容適齡 → 報告
│   ├── security_api_client.py       # VirusTotal / URLhaus / PhishTank / Google SB
│   ├── featherless_analyzer.py      # Featherless AI 分析（兒童輔導員 prompt）
│   ├── content_risk_checker.py      # Exa 抓取 + 內容適齡分類
│   └── report_generator.py          # JSON + Markdown 報告生成
│
├── second_stage/                    # API 2：勸阻分析
│   └── analyzer.py                  # 使用者理由 → 勸阻與教育 JSON + MD
│
├── tools/                           # 獨立工具
│   └── url_crawl_and_classify.py    # Exa 抓取 + Featherless 標籤分類
│
├── examples/                        # 範例輸出
│   ├── first_stage/                 # phishing / violence / porn
│   └── second_stage/                # phishing / violence / porn
│
├── .env.example                     # 環境變數範本
├── requirements.txt                 # Python 依賴
└── README.md
```

---

## 環境需求

- **Python** 3.9+
- 依賴：`requests`、`python-dotenv`

```bash
pip install -r requirements.txt
```

---

## 設定 (.env)

```bash
cp .env.example .env
```

| 變數 | 必填 | 說明 |
|------|------|------|
| `FEATHERLESS_API_KEY` | ✅ | [Featherless AI](https://featherless.ai) 金鑰 |
| `EXA_API_KEY` | ✅* | [Exa AI](https://exa.ai) 金鑰（內容適齡檢查需要） |
| `GOOGLE_SAFE_BROWSING_API_KEY` | 建議 | Google Safe Browsing v4 |
| `VIRUSTOTAL_API_KEY` | 選填 | VirusTotal API v3 |
| `PHISHTANK_API_KEY` | 選填 | PhishTank |
| `FEATHERLESS_MODEL` | 選填 | 預設 `Qwen/Qwen2.5-7B-Instruct` |
| `OUTPUT_DIR` | 選填 | 預設 `./output` |

\* 未設定 `EXA_API_KEY` 時，僅保留資安檢查結果，無法做內容適齡分析。

---

## 使用方式

所有指令從 `backend/` 目錄執行。

### 第一階段：網址分析

```bash
# 分析指定網址
python -m first_stage.main "https://example.com"

# 指定輸出目錄
python -m first_stage.main "https://example.com" -o ./reports

# 只做安全檢查，不呼叫 LLM
python -m first_stage.main "https://example.com" --skip-llm

# 使用既有 01_security_check.json，只跑 LLM + 報告
python -m first_stage.main "https://example.com" --llm-only

# 僅從既有結果生成報告
python -m first_stage.main --report-only -o ./reports

# 強制跑 LLM（即使資安風險為 low）
python -m first_stage.main "https://example.com" --force-llm
```

### 第二階段：勸阻分析

```bash
# 指定輸入檔 + 第一階段報告
python -m second_stage.analyzer \
  examples/second_stage/phishing/simulate_user_input.json \
  --first-stage examples/first_stage/phishing/03_final_report.json

# 指定輸出目錄
python -m second_stage.analyzer input.json \
  --first-stage report.json \
  -o ./my_output
```

**輸入格式** (`simulate_user_input.json`)：

```json
{
  "user_input": "使用者解釋為什麼仍想進入有害網站的理由...",
  "first_stage_report": "__LOAD_FROM_FILE__"
}
```

### 獨立工具：Exa 抓取 + 標籤分類

```bash
python -m tools.url_crawl_and_classify "https://example.com"
```

---

## 輸出檔案

### 第一階段

| 檔案 | 說明 |
|------|------|
| `01_security_check.json` | 安全平台檢查結果 |
| `02_llm_analysis.json` | 合併分析（risk_source: phishing / content / none） |
| `03_final_report.json` | 前端用報告（含 kid_friendly_summary、quiz、tips 等） |
| `03_final_report.md` | 人類可讀 Markdown |

### 第二階段

| 檔案 | 說明 |
|------|------|
| `second_stage_result.json` | 勸阻分析（行為後果、理由分析、建議、鼓勵） |
| `second_stage_result.md` | 人類可讀 Markdown |

---

## 範例輸出

```
examples/
├── first_stage/
│   ├── phishing/       # 釣魚網站（allegrolokalnie 仿冒）
│   ├── violence/       # 暴力內容（theync.com）
│   └── porn/           # 色情內容（pornhub）
└── second_stage/
    ├── phishing/       # 「賣家傳的連結、怕錯過訂單」
    ├── violence/       # 「同學都在討論、只是好奇」
    └── porn/           # 「很多人都看、就看一下」
```

---

## 備註

- 所有報告以「18 歲以下兒童輔導員」視角撰寫，避免恐嚇、用語親近。
- 第二階段採「先同理、再勸阻、附鼓勵」策略。
- 釣魚分析會預測正確網址並推薦同類型替代網站。
- 未設定的 API 金鑰會自動略過或降級處理。

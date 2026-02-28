# LO_MA_BAN Backend — 兒童網路安全網址分析

針對 18 歲以下使用者設計的網址安全與內容適齡分析後端。整合**釣魚/資安偵測**與**內容適齡檢查**，並以「兒童輔導員」視角產出 JSON 報告與互動問答。

---

## 功能概覽

| 功能 | 說明 |
|------|------|
| **釣魚／資安檢查** | VirusTotal、URLhaus、PhishTank、Google Safe Browsing 等威脅情報 |
| **內容適齡檢查** | Exa 取得網頁內容 → Featherless AI 判斷是否為情色、暴力等不當內容 |
| **分流分析** | 先做資安檢查；有風險直接標「釣魚」並分析；無風險再檢查內容是否適合兒童 |
| **兒童友善報告** | JSON 報告含風險摘要、證據卡片、互動選擇題、安全小撇步、下一步建議 |
| **第二階段勸阻** | 使用者明知有害仍想點擊時，可依「理由」產生勸阻與教育內容 |

---

## 流程架構

```
輸入 URL
    │
    ▼
┌─────────────────────────────────────┐
│ Step 1: 安全平台 API 檢查            │
│ (VirusTotal / URLhaus / PhishTank /  │
│  Google Safe Browsing)               │
└─────────────────────────────────────┘
    │
    ├─ 有風險 (critical / high / medium)
    │       │
    │       ▼
    │   【路徑 A】標註釣魚／資安風險
    │   → Featherless AI 深度分析（兒童輔導員模式）
    │   → 生成 03_final_report.json
    │
    └─ 無明顯風險 (low)
            │
            ▼
        ┌─────────────────────────────────────┐
        │ Step 2: Exa 取得網頁內容             │
        │ （失敗時改用 Exa 搜尋相關討論）       │
        └─────────────────────────────────────┘
            │
            ├─ 偵測到不當內容（色情／暴力等）
            │       │
            │       ▼
            │   【路徑 B】標註內容風險
            │   → Featherless AI 內容適齡分析
            │   → 生成 03_final_report.json
            │
            └─ 內容適合兒童
                    │
                    ▼
                【低風險】生成簡要報告
```

---

## 環境需求

- **Python** 3.9+
- 依賴見 `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## 設定 (.env)

複製 `.env.example` 為 `.env` 並填入金鑰：

```bash
cp .env.example .env
```

| 變數 | 必填 | 說明 |
|------|------|------|
| `FEATHERLESS_API_KEY` | ✅ | [Featherless AI](https://featherless.ai) 金鑰，用於分析與報告生成 |
| `EXA_API_KEY` | ✅* | [Exa AI](https://exa.ai) 金鑰，用於抓取／搜尋網頁內容（內容適齡檢查需要） |
| `GOOGLE_SAFE_BROWSING_API_KEY` | 建議 | Google Safe Browsing v4，資安檢查 |
| `VIRUSTOTAL_API_KEY` | 選填 | VirusTotal API v3 |
| `PHISHTANK_API_KEY` | 選填 | PhishTank |
| `FEATHERLESS_MODEL` | 選填 | 預設 `Qwen/Qwen2.5-7B-Instruct` |
| `OUTPUT_DIR` | 選填 | 預設 `./output` |
| `DEFAULT_TARGET_URL` | 選填 | 未傳 URL 時使用的預設網址 |

\* 未設定 `EXA_API_KEY` 時，資安無風險的 URL 將無法做內容適齡檢查，僅保留資安結果。

---

## 使用方式

### 主流程：分析單一網址

```bash
# 分析指定網址（輸出到預設 ./output）
python main.py "https://example.com"

# 指定輸出目錄
python main.py "https://example.com" -o ./reports

# 只做安全檢查，不呼叫 LLM
python main.py "https://example.com" --skip-llm

# 使用既有 01_security_check.json，只跑 LLM + 報告
python main.py "https://example.com" --llm-only

# 僅從既有結果生成報告
python main.py --report-only -o ./reports

# 強制跑 LLM（即使資安風險為 low）
python main.py "https://example.com" --force-llm
```

### 第二階段：明知有害仍想點擊的勸阻

需自備輸入 JSON（含 `user_input` 與 `first_stage_report`），或搭配 `--first-stage` 使用既有報告：

```bash
# 使用內建 test 輸入（需先準備含 user_input + first_stage_report 的 JSON）
python second_stage_analyzer.py

# 指定輸入檔 + 第一階段報告
python second_stage_analyzer.py my_input.json --first-stage output/03_final_report.json
```

輸出寫入 `test_second_stage_output.json`，內含行為後果警告、理由分析、一般安全提醒。

### 獨立腳本：網址爬取 + 標籤分類

不經過主流程，僅「Exa 抓內容 → Featherless 標籤」：

```bash
python url_crawl_and_classify.py "https://example.com"
# 結果：url_classification_result.json（若未改程式則寫入同目錄）
```

---

## 輸出檔案結構

執行 `main.py` 後，於 `-o` 指定目錄（或 `OUTPUT_DIR`）會產生：

| 檔案 | 說明 |
|------|------|
| `01_security_check.json` | 各安全平台檢查結果、整體風險、critical_flags 等 |
| `02_llm_analysis.json` | 合併資安／內容分析、risk_source、final_risk_level、llm_analysis |
| `03_final_report.json` | 前端用報告：report_metadata、kid_friendly_summary、evidence_cards、interactive_quiz、safety_tips、next_steps、raw_analysis |

`risk_source` 可能為：

- `phishing` — 來自資安風險（釣魚／惡意網址）
- `content` — 來自內容適齡（不適合兒童）
- `none` — 低風險或無法取得內容

---

## 專案結構

```
backend/
├── main.py                    # 主程式：資安 → 內容適齡 → 報告
├── config.py                  # 設定與 .env 讀取
├── security_api_client.py     # VirusTotal / URLhaus / PhishTank / Google SB
├── featherless_analyzer.py    # Featherless 分析（資安 + 內容風險）、兒童輔導員 prompt
├── content_risk_checker.py    # Exa 抓取 + 內容適齡分類、is_unsuitable_for_children
├── report_generator.py       # 03_final_report.json 生成（兒童友善文案、問答、tips）
├── url_crawl_and_classify.py # 獨立：Exa 抓取 + Featherless 標籤分類
├── second_stage_analyzer.py   # 第二階段：依「想點擊理由」產生勸阻 JSON
├── scam_analyzer_prompt.py   # 舊版／備用 prompt 建構
├── utils.py                   # save_json、load_json、step_marker 等
├── requirements.txt
├── .env.example
└── README.md                  # 本說明
```

---

## 授權與備註

- 報告文案與問答以「18 歲以下兒童輔導員」視角撰寫，避免過度恐嚇、用語親近。
- 依實際需求在 `.env` 中設定各 API 金鑰；未設定的服務會略過或降級處理。

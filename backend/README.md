# 🔍 Scam Analyzer v2 - 網站安全分析與互動教學系統

> 一個結合多個威脅情報平台 API 與 AI 深度分析的網站安全檢測工具，專為 18 歲以下學習者設計互動式教學報告。

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Development-yellow.svg)

---

## 📋 目錄

- [✨ 功能特色](#-功能特色)
- [🏗️ 系統架構](#️-系統架構)
- [📦 安裝需求](#-安裝需求)
- [⚙️ 環境設定](#️-環境設定)
- [🔑 API Key 申請教學](#-api-key-申請教學)
- [🚀 快速開始](#-快速開始)
- [📊 輸出格式說明](#-輸出格式說明)
- [🧩 互動選擇題設計](#-互動選擇題設計)
- [🔧 常見問題排除](#-常見問題排除)
- [📁 專案結構](#-專案結構)
- [🤝 貢獻指南](#-貢獻指南)
- [📄 授權說明](#-授權說明)

---

## ✨ 功能特色

### 🔐 多重安全平台整合
- **VirusTotal**: 70+ 安全引擎掃描結果
- **URLhaus**: 惡意軟體 URL 即時資料庫
- **PhishTank**: 社群維護的釣魚網站清單
- **Google Safe Browsing**: Google 官方威脅情報

### 🤖 AI 深度分析
- 使用 **Featherless AI** (Qwen2.5-7B-Instruct) 進行風險解釋
- 自動生成兒童友善的風險說明
- 結構化 JSON 輸出，前端可直接渲染

### 🧒 互動式教學設計
- 簡化專業術語，使用親切語氣與 emoji
- 自動生成創意選擇題（LLM 發揮，不寫死格式）
- 每個選項附「為什麼對/錯」的詳細解釋
- 視覺化風險卡片與安全小撇步

### 📦 彈性輸出格式
- **JSON**: 前端可直接使用的結構化資料
- **Markdown**: 人類可讀的完整報告（可選）
- 每步驟自動儲存中間結果，方便除錯

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────┐
│              使用者輸入 URL              │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│         Step 1: 安全平台 API 檢查        │
│  ┌─────────┬─────────┬─────────┐       │
│  │VirusTotal│ URLhaus │PhishTank│ ... │
│  └─────────┴─────────┴─────────┘       │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│         Step 2: LLM 深度分析             │
│  • 解釋為什麼被標記為不安全              │
│  • 生成兒童友善的風險說明                │
│  • 創意互動選擇題（4 選項 + 解釋）        │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│         Step 3: 生成教學報告             │
│  • JSON 輸出：前端可直接渲染             │
│  • 包含：風險摘要、證據卡片、互動測驗等  │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│              前端互動教學                │
│  • 風險視覺化 • 選擇題互動 • 安全建議   │
└─────────────────────────────────────────┘
```

---

## 📦 安裝需求

### 🔧 Python 環境
```bash
# 建議使用 Python 3.9+
python --version  # 應顯示 Python 3.9.x 或更高

# 建立虛擬環境（推薦）
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows
```

### 📋 套件安裝
```bash
# 安裝所有依賴
pip install -r requirements.txt

# 或手動安裝主要套件
pip install requests python-dotenv pathlib typing-extensions
```

### 📄 requirements.txt 範例
```txt
requests>=2.28.0
python-dotenv>=1.0.0
pathlib>=1.0.1
typing-extensions>=4.5.0
```

---

## ⚙️ 環境設定

### 1️⃣ 建立 `.env` 檔案
```bash
# 複製範例（如果有的話）
cp .env.example .env

# 或直接建立
touch .env
```

### 2️⃣ 填寫 API Keys
```bash
# === App Settings ===
DEFAULT_TARGET_URL=
OUTPUT_DIR=./output
SAVE_INTERMEDIATE=true

# === Security API Keys ===
API_TIMEOUT=30

# URLhaus (免費註冊: https://auth.abuse.ch/)
URLHAUS_AUTH_KEY=your_auth_key_here

# VirusTotal (免費註冊: https://www.virustotal.com/gui/my-apikey)
VIRUSTOTAL_API_KEY=your_vt_key_here

# PhishTank (免費註冊: https://phishtank.com/api_key.php)
PHISHTANK_API_KEY=your_phishtank_key_here

# Google Safe Browsing (需要 GCP 專案)
GOOGLE_SAFE_BROWSING_API_KEY=your_google_key_here

# === Featherless AI ===
FEATHERLESS_API_KEY=your_featherless_key_here
FEATHERLESS_MODEL=Qwen2.5-7B-Instruct
FEATHERLESS_API_URL=https://api.featherless.ai/v1/chat/completions
FEATHERLESS_TEMPERATURE=0.1
FEATHERLESS_MAX_TOKENS=2000
```

### 3️⃣ 確認 `config.py` 設定
確保 `config.py` 包含以下設定類別：

```python
# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # App Settings
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./output"))
    SAVE_INTERMEDIATE: bool = os.getenv("SAVE_INTERMEDIATE", "true").lower() == "true"
    DEFAULT_TARGET_URL: str = os.getenv("DEFAULT_TARGET_URL", "")
    
    # API Settings
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    
    # Security APIs
    URLHAUS_AUTH_KEY: str = os.getenv("URLHAUS_AUTH_KEY", "")
    URLHAUS_BASE_URL: str = "https://urlhaus-api.abuse.ch/v1"
    
    VIRUSTOTAL_API_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    VIRUSTOTAL_BASE_URL: str = "https://www.virustotal.com/api/v3"
    
    PHISHTANK_API_KEY: str = os.getenv("PHISHTANK_API_KEY", "")
    PHISHTANK_BASE_URL: str = "https://api.phishtank.com/v2/phishtank/verify"
    
    GOOGLE_SAFE_BROWSING_API_KEY: str = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    GOOGLE_SAFE_BROWSING_BASE_URL: str = "https://safebrowsing.googleapis.com/v4"
    
    # Featherless AI
    FEATHERLESS_API_URL: str = os.getenv("FEATHERLESS_API_URL", "https://api.featherless.ai/v1/chat/completions")
    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    FEATHERLESS_MODEL: str = os.getenv("FEATHERLESS_MODEL", "Qwen2.5-7B-Instruct")
    FEATHERLESS_TEMPERATURE: float = float(os.getenv("FEATHERLESS_TEMPERATURE", "0.1"))
    FEATHERLESS_MAX_TOKENS: int = int(os.getenv("FEATHERLESS_MAX_TOKENS", "2000"))
    
    @classmethod
    def setup_output_dir(cls):
        """建立輸出目錄"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return cls.OUTPUT_DIR
    
    @classmethod
    def validate(cls) -> list[str]:
        """驗證必要設定"""
        errors = []
        if not cls.FEATHERLESS_API_KEY:
            errors.append("FEATHERLESS_API_KEY 未設定")
        # 至少需要一個安全 API
        if not any([cls.URLHAUS_AUTH_KEY, cls.VIRUSTOTAL_API_KEY, cls.PHISHTANK_API_KEY, cls.GOOGLE_SAFE_BROWSING_API_KEY]):
            errors.append("至少需要設定一個安全平台 API Key")
        return errors
```

---

## 🔑 API Key 申請教學

### 🟢 URLhaus Auth-Key（完全免費，推薦首選）
1. 前往 https://auth.abuse.ch/
2. 註冊帳號（只需 email）
3. 登入後複製 **Auth-Key**（40 字元）
4. 填入 `.env` 的 `URLHAUS_AUTH_KEY`

### 🟡 VirusTotal API Key（免費層足夠個人使用）
1. 前往 https://www.virustotal.com/
2. 註冊免費帳號
3. 進入 **API Key** 頁面：https://www.virustotal.com/gui/my-apikey
4. 複製 API Key 填入 `.env`
5. ⚠️ 免費層限制：4 次/分鐘，500 次/天

### 🔵 PhishTank API Key（免費，功能有限）
1. 前往 https://phishtank.com/api_key.php
2. 註冊帳號並申請 API Key
3. ⚠️ 免費 API 功能較有限，建議作為輔助來源

### 🔴 Google Safe Browsing API Key（需要 GCP 專案）
1. 前往 https://console.cloud.google.com/
2. 建立新專案或選擇現有專案
3. 啟用 **Safe Browsing API**：
   ```
   API 與服務 > 程式庫 > 搜尋 "Safe Browsing" > 啟用
   ```
4. 建立 API Key：
   ```
   API 與服務 > 憑證 > 建立憑證 > API 金鑰
   ```
5. （建議）限制 API Key 僅允許 Safe Browsing API 使用
6. ⚠️ 免費層：10,000 次/月

### 🟣 Featherless AI API Key
1. 前往 Featherless AI 官方平台申請
2. 取得 API Key 與 API Endpoint
3. 填入 `.env` 的 `FEATHERLESS_API_KEY` 與 `FEATHERLESS_API_URL`

---

## 🚀 快速開始

### 🔹 基本使用
```bash
# 完整流程：安全檢查 + LLM 分析 + JSON 報告
python main.py "https://suspicious-site.cfd/login"

# 指定輸出目錄
python main.py "https://example.com" -o ./reports
```

### 🔹 進階指令
```bash
# 只執行安全 API 檢查（不呼叫 LLM）
python main.py "https://example.com" --skip-llm

# 使用現有安全結果，只呼叫 LLM 分析
python main.py "https://example.com" --llm-only

# 強制呼叫 LLM（即使風險等級低）
python main.py "https://gemini.google.com/" --force-llm

# 僅從現有 JSON 生成報告
python main.py --report-only

# 讀取預設目標網址（從 .env 的 DEFAULT_TARGET_URL）
python main.py
```

### 🔹 執行流程日誌範例
```
2026-02-28 17:02:26 - INFO - 🔍 Scam Analyzer v2 - 安全平台 API + Featherless AI
2026-02-28 17:02:26 - INFO - 🎯 目標網址：https://example.cfd
2026-02-28 17:02:26 - INFO - 🔄 [Step 1] 執行安全平台 API 檢查
2026-02-28 17:02:29 - INFO - ✅ 檢查完成，整體風險：high
2026-02-28 17:02:29 - INFO - 🔄 [Step 2] 風險等級：high，開始 LLM 深度分析
2026-02-28 17:02:58 - INFO - ✅ Featherless 分析完成
2026-02-28 17:02:58 - INFO - 🔄 [Step 3] 生成 JSON 報告
2026-02-28 17:02:58 - INFO - 📦 JSON 報告已儲存：output/03_final_report.json

📋 分析結果摘要
============================================================
🎯 目標：https://example.cfd
🚨 風險等級：HIGH
💡 威脅摘要：高度疑似釣魚網站，模仿知名品牌
📝 建議：['避免輸入個資', '用官方網址訪問']
💾 完整報告：output/03_final_report.json
```

---

## 📊 輸出格式說明

### 📁 輸出檔案結構
```
output/
├── 01_security_check.json    # 安全平台 API 原始結果
├── 02_llm_analysis.json      # LLM 深度分析結果
└── 03_final_report.json      # ✅ 前端可用的最終報告（JSON）
```

### 📦 `03_final_report.json` 結構
```json
{
  "report_metadata": {
    "target_url": "https://example.cfd",
    "target_domain": "example.cfd",
    "target_tld": "cfd",
    "timestamp": "2026-02-28T17:02:58",
    "risk": {
      "level": "high",
      "score": 75,
      "icon": "🔴",
      "color": "#f97316",
      "label": "很危險"
    },
    "confidence": {
      "level": "high",
      "icon": "✅",
      "label": "很確定"
    }
  },
  "kid_friendly_summary": {
    "title": "🔴 很危險！",
    "simple_message": "⚠️ 這個網站看起來怪怪的，建議不要訪問",
    "short_explanation": "這個網址有幾個紅燈信號：...",
    "emoji_reaction": "🔴",
    "action_verb": "不要點"
  },
  "evidence_cards": [
    {
      "id": "evidence_1",
      "icon": "🌐",
      "title": "🌐 .cfd 域名風險",
      "content": ".cfd 是非常規頂級域名，多數同類域名被標記為低信任",
      "severity": "high",
      "expandable": true
    }
  ],
  "interactive_quiz": {
    "enabled": true,
    "question": "🔍 你覺得這個網址哪裡怪怪的？",
    "hint": "仔細看每個字母喔，騙子喜歡用數字代替字母！",
    "type": "single_choice",
    "options": [
      {
        "id": "A",
        "text": "它跟真正的品牌網址長得好像，但有些地方不太一樣",
        "is_correct": false,
        "explanation": "只注意到「像」還不夠，要學會「逐字檢查每個字母」喔！",
        "feedback_icon": "❌"
      },
      {
        "id": "B",
        "text": "它的「尾巴」是 .cfd，但正規網站通常是 .com",
        "is_correct": false,
        "explanation": ".cfd 確實可疑，但騙子也會用 .com，不能只看尾巴",
        "feedback_icon": "❌"
      },
      {
        "id": "C",
        "text": "它用數字或符號代替字母（例如用 1 代替 l，0 代替 o）",
        "is_correct": true,
        "explanation": "答對啦！騙人的網站常用數字代替字母來混淆你，要逐字檢查！",
        "feedback_icon": "✅"
      },
      {
        "id": "D",
        "text": "以上都是！🎉",
        "is_correct": false,
        "explanation": "D 看起來很誘人，但這題要選「最關鍵」的那個喔！",
        "feedback_icon": "❌"
      }
    ],
    "correct_answer_id": "C",
    "learning_point": "看到很像知名品牌的網址，一定要「逐字檢查」＋「確認官方網址」！",
    "difficulty": "medium"
  },
  "safety_tips": [
    {
      "id": "tip_1",
      "icon": "🔍",
      "tip": "不隨便點陌生連結",
      "why": "陌生連結可能帶你到騙人的網站",
      "action_text": "記住囉！"
    }
  ],
  "next_steps": [
    {"action": "❌ 不要點擊此連結", "priority": "high", "icon": "🚫"},
    {"action": "🔍 用 VirusTotal 再檢查一次", "priority": "medium", "icon": "🔎", "link": "https://www.virustotal.com"}
  ]
}
```

---

## 🧩 互動選擇題設計

### 🎯 設計原則
1. **不寫死格式**：讓 LLM 自由發揮創意（情境題、找不同、排序題等）
2. **兒童友善語言**：避免專業術語，使用「騙人的假網站」、「壞壞的程式」等詞彙
3. **完整解釋**：每個選項都有「為什麼對/錯」的說明
4. **學習導向**：題目目標是教會讀者辨識技巧，而非單純測驗

### 🔄 LLM Prompt 設計
在 `featherless_analyzer.py` 中，系統提示詞包含：
```
🎮 **互動教學任務（JSON 輸出）**：
請額外生成一個「創意選擇題」，幫助讀者學習辨識可疑網址。
要求：
1. 題目要有趣、不寫死格式（可以是情境題、找不同、排序題等）
2. 提供 4 個選項（A/B/C/D）
3. 標明正確答案
4. 每個選項都要有「為什麼對/錯」的簡單解釋（小朋友聽得懂的語言）
5. 可選：加一個小提示（hint）增加趣味性
```

### 🧱 Fallback 機制
如果 LLM 未生成題目或格式錯誤，系統會自動使用預設模板：
- **品牌仿冒題**：針對 `paypa1.com` 類型的釣魚網址
- **TLD 風險題**：針對 `.cfd`、`.xyz` 等非常規域名
- **通用安全題**：基礎網路安全意識測驗

---

## 🔧 常見問題排除

### ❌ `AttributeError: type object 'Config' has no attribute 'XXX'`
**原因**：`config.py` 缺少對應設定變數  
**解法**：在 `Config` class 中加入：
```python
XXX: str = os.getenv("XXX", "")
```

### ❌ `TypeError: unhashable type: 'dict'`
**原因**：LLM 回傳的 `options` 是 dict 列表，但程式碼假設是文字列表  
**解法**：更新 `report_generator.py` 的 `_render_llm_quiz` 方法，加入類型檢查：
```python
if isinstance(opt, dict):
    opt_id = opt.get('id', ...)
    opt_text = opt.get('text', str(opt))
else:
    opt_id = ...
    opt_text = str(opt)
```

### ❌ `401 Unauthorized`（URLhaus/VirusTotal）
**原因**：API Key 無效或未設定  
**解法**：
1. 確認 `.env` 中已填寫正確的 API Key
2. 確認 API Key 已啟用且有配額
3. 清除 Python cache 後重試：
   ```bash
   find . -name "__pycache__" -exec rm -rf {} +
   ```

### ❌ `404 Not Found`（Google Safe Browsing）
**原因**：API 端點格式錯誤  
**解法**：確認使用正確端點：
```python
# ✅ 正確
endpoint = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
# ❌ 錯誤
endpoint = "https://safebrowsing.googleapis.com/v4/threatMatches:findFullHash"
```

### ❌ 輸出還是 `.md` 不是 `.json`
**原因**：`main.py` 的輸出路徑設定錯誤  
**解法**：確認以下兩處：
```python
# main.py - Step 3
report_output = output_dir / "03_final_report.json"  # ✅ 確保副檔名是 .json

# report_generator.py - generate_report 方法
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)  # ✅ 使用 json.dump
```

### ❌ LibreSSL 警告（Mac 用戶）
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```
**解法**（三選一）：
```bash
# 方案 A：忽略警告（最快）
export PYTHONWARNINGS="ignore::urllib3.exceptions.NotOpenSSLWarning"

# 方案 B：降級 urllib3
pip install 'urllib3<2.0'

# 方案 C：升級 Python（長期解法）
brew install python@3.11
```

---

## 📁 專案結構

```
LO_MA_BAN/
├── .env                          # 🔐 環境變數與 API Keys
├── .env.example                  # 📋 環境變數範例
├── .gitignore                    # 🚫 Git 忽略檔案
├── README.md                     # 📖 本文件
├── requirements.txt              # 📦 Python 依賴套件
│
├── config.py                     # ⚙️ 設定檔（Config class）
├── utils.py                      # 🔧 工具函數（save_json, load_json...）
│
├── main.py                       # 🚀 主程式入口
├── security_api_client.py        # 🔐 安全平台 API 客戶端
├── featherless_analyzer.py       # 🤖 Featherless AI 分析器
├── report_generator.py           # 📦 JSON 報告生成器
│
├── archive/                      # 🗄️ 舊架構模組（可選封存）
│   ├── prompt_builder.py
│   ├── scam_analyzer_prompt.py
│   └── exa_query.py
│
├── output/                       # 📁 輸出目錄（自動建立）
│   ├── 01_security_check.json
│   ├── 02_llm_analysis.json
│   └── 03_final_report.json
│
└── tests/                        # 🧪 測試檔案（可選）
    ├── test_security_api.py
    └── test_report_generator.py
```

---

## 🤝 貢獻指南

歡迎貢獻程式碼、文件或建議！🎉

### 🔧 開發流程
1. Fork 本專案
2. 建立功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add: your feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 開啟 Pull Request

### 📝 程式碼規範
- 遵循 PEP 8 Python 風格指南
- 函數與類別添加 docstring
- 日誌使用 `logging` 模組，避免 `print`
- 錯誤處理加入適當的 fallback 機制

### 🧪 測試建議
```bash
# 測試單一 API 呼叫
python -c "
from security_api_client import SecurityAPIClient
client = SecurityAPIClient()
result = client.check_urlhaus('https://example.com')
print(result)
"

# 測試報告生成
python -c "
from report_generator import ReportGenerator
from pathlib import Path
# ... 載入測試資料並生成報告
"
```

---

## 📄 授權說明

本專案採用 **MIT License** 授權。

```
MIT License

Copyright (c) 2026 Scam Analyzer Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

> ⚠️ **免責聲明**：本工具僅供教育與研究用途，檢測結果僅供參考，不構成專業安全建議。對於因使用本工具產生的任何損失，作者不承擔法律責任。

---

**🔐 安全口訣**：「陌生連結不亂點，先查再按最安全！」✨
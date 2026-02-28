/**
 * 網頁爬取 + AI 標籤分類 (JavaScript/Node.js)
 * 1. 使用 Exa API 爬取指定 URL 的網頁內容
 * 2. 將內容送至 Featherless AI 判斷網頁屬於什麼標籤
 *
 * 使用方式（需 Node 18+）:
 *   node url_crawl_and_classify.js "https://example.com"
 *   node url_crawl_and_classify.js "https://allegrolokalnie.pl-oferta-id-133457.cfd"
 *
 * 環境變數: EXA_API_KEY, FEATHERLESS_API_KEY
 * 可用 dotenv: npm install dotenv
 */

const EXA_API_KEY = process.env.EXA_API_KEY || "";
const FEATHERLESS_API_KEY = process.env.FEATHERLESS_API_KEY || "";
const FEATHERLESS_API_URL = process.env.FEATHERLESS_API_URL || "https://api.featherless.ai/v1/chat/completions";
const FEATHERLESS_MODEL = process.env.FEATHERLESS_MODEL || "Qwen/Qwen2.5-7B-Instruct";

// ========== 方法一：直接抓取 URL 內容 ==========
async function fetchUrlContentExa(targetUrl) {
  const response = await fetch("https://api.exa.ai/contents", {
    method: "POST",
    headers: {
      "x-api-key": EXA_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      urls: [targetUrl],
      text: true,
      highlights: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Exa API 錯誤: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  const results = data.results || [];

  if (results.length === 0) {
    const statuses = data.statuses || [];
    const errStatus = statuses.find((s) => s.status === "error");
    if (errStatus?.error) {
      throw new Error(`Exa 爬取失敗: ${errStatus.error.tag || "unknown"}`);
    }
    throw new Error("Exa 未回傳任何內容");
  }

  const parts = [];
  for (const r of results) {
    if (r.text) parts.push(r.text);
    if (r.highlights) {
      for (const h of Array.isArray(r.highlights) ? r.highlights : [r.highlights]) {
        parts.push(typeof h === "string" ? h : h?.text || h?.snippet || "");
      }
    }
  }
  const content = parts.filter(Boolean).join("\n\n").trim();
  if (!content) throw new Error("Exa 回傳的內容為空");
  return content;
}

// ========== 方法二：搜尋網路上關於此 URL 的討論 ==========
async function searchUrlContextExa(targetUrl, numResults = 5) {
  const response = await fetch("https://api.exa.ai/search", {
    method: "POST",
    headers: {
      "x-api-key": EXA_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: targetUrl,
      type: "auto",
      numResults,
      contents: { text: true, summary: true },
    }),
  });

  if (!response.ok) {
    throw new Error(`Exa 搜尋錯誤: ${response.status}`);
  }

  const data = await response.json();
  const results = data.results || [];
  if (!results.length) throw new Error("Exa 搜尋無結果");

  const parts = results.flatMap((r) => [
    r.text,
    r.summary ? `[摘要] ${r.summary}` : null,
  ]).filter(Boolean);
  return parts.join("\n\n").trim();
}

// ========== Featherless AI 標籤分類 ==========
async function classifyWithFeatherless(url, pageContent) {
  const maxChars = 8000;
  const truncated = pageContent.length > maxChars
    ? pageContent.slice(0, maxChars) + "\n\n[... 內容已截斷 ...]"
    : pageContent;

  const systemPrompt = `你是一位專業的網頁內容分類專家。請根據提供的網頁 URL 與內容，判斷這個網頁屬於什麼標籤。

請輸出結構化 JSON，格式如下：
{
  "labels": ["標籤1", "標籤2", "標籤3"],
  "primary_label": "主要標籤",
  "confidence": "high/medium/low",
  "explanation": "簡短說明為什麼歸類為這些標籤（50–100字）"
}

標籤範例：詐騙、釣魚、惡意、購物、電商、新聞、社交、金融、政府、教育、娛樂、不明、可疑等。`;

  const userContent = `請分析以下網頁並判斷其標籤：

URL: ${url}

網頁內容：
---
${truncated}
---

請輸出 JSON 格式的分類結果。`;

  const response = await fetch(FEATHERLESS_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${FEATHERLESS_API_KEY}`,
    },
    body: JSON.stringify({
      model: FEATHERLESS_MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent },
      ],
      temperature: 0.1,
      max_tokens: 500,
      stream: false,
      response_format: { type: "json_object" },
    }),
  });

  if (!response.ok) {
    throw new Error(`Featherless API 錯誤: ${response.status}`);
  }

  const result = await response.json();
  const content = result.choices?.[0]?.message?.content;
  if (!content) throw new Error("Featherless 回傳格式異常");

  return JSON.parse(content);
}

// ========== Main ==========
async function main() {
  const useSearch = process.argv.includes("--search");
  const targetUrl = process.argv.find((a) => a.startsWith("http")) || "https://example.com";

  if (!EXA_API_KEY) {
    console.error("❌ EXA_API_KEY 未設定");
    process.exit(1);
  }
  if (!FEATHERLESS_API_KEY) {
    console.error("❌ FEATHERLESS_API_KEY 未設定");
    process.exit(1);
  }

  console.log(`🎯 目標網址: ${targetUrl}\n`);

  let content;
  try {
    if (useSearch) {
      console.log("📡 使用 Exa 搜尋模式...");
      content = await searchUrlContextExa(targetUrl);
    } else {
      console.log("📡 使用 Exa 直接抓取網頁內容...");
      content = await fetchUrlContentExa(targetUrl);
    }
  } catch (e) {
    console.error("❌", e.message);
    process.exit(1);
  }

  console.log(`✅ 取得內容，共 ${content.length} 字\n`);
  console.log("🤖 呼叫 Featherless AI 進行標籤分類...");

  let classification;
  try {
    classification = await classifyWithFeatherless(targetUrl, content);
  } catch (e) {
    console.error("❌", e.message);
    process.exit(1);
  }

  const output = {
    target_url: targetUrl,
    content_length: content.length,
    content_preview: content.slice(0, 500) + (content.length > 500 ? "..." : ""),
    classification,
  };

  const fs = await import("fs");
  fs.writeFileSync("url_classification_result.json", JSON.stringify(output, null, 2), "utf8");
  console.log("✅ 結果已儲存至: url_classification_result.json\n");
  console.log("=".repeat(50));
  console.log("📋 分類結果");
  console.log("=".repeat(50));
  console.log(`  主要標籤: ${classification.primary_label || "N/A"}`);
  console.log(`  標籤列表: ${(classification.labels || []).join(", ")}`);
  console.log(`  信心程度: ${classification.confidence || "N/A"}`);
  console.log(`  說明: ${classification.explanation || "N/A"}`);
}

main().catch(console.error);

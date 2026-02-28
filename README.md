# ScoutNet - AI-Powered Online Safety Guide for Children

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Chrome Web Store](https://img.shields.io/badge/Chrome-Extension-blue.svg)](https://chrome.google.com/webstore)
[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)](https://github.com/your-repo/scoutnet)

---

## Table of Contents
- [Executive Summary](#executive-summary)
- [Product Philosophy](#product-philosophy)
- [Target Audience](#target-audience)
- [Core Features](#core-features)
- [User Flow](#user-flow)
- [Technical Architecture](#technical-architecture)
- [AI Integration](#ai-integration)
- [Installation Guide](#installation-guide)
- [Development Roadmap](#development-roadmap)
- [Open Questions](#open-questions)
- [Team](#team)
- [License](#license)

---

## Executive Summary

**ScoutNet** is a Chrome extension designed for children under 18 that reimagines online safety. Unlike traditional parental control tools that rely on blocking and surveillance, ScoutNet takes a **privacy-first**, **guidance-based** approach.

By leveraging AI to analyze web content in real-time, we transform everyday browsing into opportunities for building digital literacy. When a potential risk is detected, the system pauses navigation and engages the child in a Socratic dialogue—guiding them to recognize threats themselves rather than simply blocking access.

| Traditional Tools | ScoutNet Approach |
|------------------|-------------------|
| Blocking without explanation | Guided conversation about risks |
| Background surveillance | Privacy-first, local processing |
| Parental control | Child empowerment |
| Fear-based | Education-based |

---

## Product Philosophy

| Principle | Description |
|-----------|-------------|
| **Guidance over Restriction** | Instead of just saying "no," we explain "why" and ensure the child understands. |
| **Empowerment over Surveillance** | Our goal is to help children develop independent judgment, not to monitor their behavior. |
| **Transparency & Privacy** | Our risk criteria are transparent, and we respect children's data privacy. |

---

## Target Audience

### Primary Users: Children (under 18 years old)

| Profile | Characteristics |
|---------|-----------------|
| Age | Under 18 years old |
| Reading Level | Basic reading and typing skills |
| Internet Usage | Regular browsing for schoolwork and entertainment |
| Risk Awareness | Limited awareness of phishing, cyberbullying, and privacy risks |

### Secondary Users: Parents/Guardians

| Profile | Characteristics |
|---------|-----------------|
| Goal | Want to protect children without damaging trust |
| Concern | Existing tools feel like surveillance, not guidance |
| Need | Tools that teach children to protect themselves |

---

## Core Features

### 4.1. Default Block with AI Scanning

To ensure safety, we use a "zero-trust" loading strategy.

| Feature ID | Description | User Experience |
|------------|-------------|-----------------|
| **FR-001** | Default Block | When user enters a URL or clicks a link, ScoutNet immediately shows an overlay with a friendly scanning animation: "ScoutNet is checking this site for you..." |
| **FR-002** | URL Analysis & Risk Query | System extracts the URL. Calls **4 Security APIs** (VirusTotal, URLhaus, PhishTank, Google Safe Browsing) in parallel for threat intelligence. If no security risk is found, **Exa AI** fetches page content for age-suitability analysis. |
| **FR-003** | Risk Assessment & Routing | - **Safe**: AI determines no risk, overlay fades out, normal browsing resumes. Green shield icon appears in corner.<br>- **Phishing/Security Risk**: Enters Path A — deep phishing analysis via Featherless AI.<br>- **Inappropriate Content**: Enters Path B — content risk analysis via Featherless AI. |

### 4.2. Conversational Guidance Mode

This is ScoutNet's core differentiator—turning blocking into education.

| Feature ID | Description | Details |
|------------|-------------|---------|
| **FR-004** | Risk Scenario Generation | Calls **Featherless AI (Qwen)** to generate age-appropriate warnings and guiding questions based on the detected risk type (phishing or inappropriate content). |
| **FR-005** | Interactive Overlay | Screen remains blurred. A dialogue box appears asking contextual questions. For example:<br><br>**Question**: 你覺得 `allegrolokalnie.pl-oferta-id-133457-kategorie-id-192876.cfd` 這個網址，哪裡「怪怪的」？<br>(A) 它跟真正的品牌網址長得好像，但有些地方不太一樣 ❌<br>(B) 它的「尾巴」是 .cfd，但正規網站通常是 .com ❌<br>(C) 它用數字或符號代替字母（例如用 1 代替 l，0 代替 o） ✅<br>(D) 以上都是！ ❌ |
| **FR-006** | Unlock Logic | Child must answer the question. AI evaluates response:<br>• **Pass**: "Great job! You recognized the risk." Overlay fades, warning icon remains in corner.<br>• **Fail**: AI explains the correct answer, may ask again or suggest leaving. |

### 4.3. Second-Stage Persuasion & Education

When users still want to access a risky site after seeing the report, a second stage of AI-driven persuasion kicks in.

| Feature ID | Description | Details |
|------------|-------------|---------|
| **FR-007** | Reason Input | User is prompted to explain why they still want to enter the site. |
| **FR-008** | AI Persuasion Analysis | Featherless AI analyzes the user's stated reason, provides empathetic but firm guidance including behavior consequence warnings, general warnings, and recommended actions. |
| **FR-009** | Final Decision | Based on `is_reasonable` judgment:<br>• **Reasonable**: Allow access with persistent warning markers.<br>• **Unreasonable**: Show encouraging message suggesting to leave, but still allow "insist access" as last resort. |

---

## User Flow

### Complete Interaction Flow

![User Flow Diagram](dev-doc/user_flow_v2.jpg)

### Flow Description

The diagram illustrates ScoutNet's complete URL scanning and risk education pipeline:

**1. Trigger**
User clicks a link or enters a URL, triggering ScoutNet's background service worker.

**2. Security Scanning (4 APIs in Parallel)**
The URL is immediately sent to four security intelligence APIs — VirusTotal, URLhaus, PhishTank, and Google Safe Browsing — running in parallel for maximum speed.

**3. Risk Routing**

- **Path A — Phishing Detected**: If any security API flags the URL as malicious, ScoutNet calls **Featherless AI** for deep phishing analysis. The AI generates a child-friendly security report including predicted intended URLs, alternative safe websites, evidence cards, an interactive quiz, and safety tips.

- **Path B — No Security Risk**: The URL is passed to **Exa AI** to fetch the actual page content. If the fetch fails, ScoutNet falls back to searching related content (e.g. from Reddit or other sources).
  - **Featherless AI** then classifies whether the content is child-friendly.
  - **Child-friendly** → User enters the site directly.
  - **Not child-friendly** → A content risk report is generated (same structure as phishing reports).

**4. URL Security Analysis Report**
The report is presented as an interactive overlay containing:
- Verified safe URL information & executive summary
- Recommended actions
- FAQ & interactive support (quiz)

**5. User Decision — "Still want to access?"**
- **No** → Break. The user leaves safely.
- **Yes** → The user must provide a reason for why they still want to enter.

**6. Second-Stage Persuasion**
The user's reason is sent to **Featherless AI**, which responds with empathetic persuasion and education — including behavior consequence warnings, empathy notes, and encouraging messages.

**7. Final Outcome**
- If the user accepts the guidance → Break (leave).
- If the user insists on accessing → Enter (with persistent risk markers).

---

## Technical Architecture

### Frontend (Client-side)
- **Platform**: Chrome Extension (Manifest V3)
- **Framework**: React + TypeScript (Vite-based)
- **Key Components**:
  - `Background Service Worker`: URL interception, API request forwarding
  - `Content Script`: Overlay injection, UI state management
  - `Popup`: Settings and auxiliary interface

### AI & Backend Services
- **Security Intelligence**: VirusTotal, URLhaus, PhishTank, Google Safe Browsing (parallel async queries)
- **Content Retrieval**: **Exa AI** (fetches real page content for age-suitability analysis)
- **Generative AI**: **Qwen via Featherless AI** (generates child-friendly dialogue, evaluates responses, persuasion analysis)
- **Backend Framework**: FastAPI (Python, fully async)

For detailed backend API documentation, see [backend/README.md](backend/README.md).

---

## Development Roadmap

### Phase 1: MVP (Current)
- Complete Chrome Extension base architecture.
- Implement "default block" + Security APIs + Exa/Qwen API integration.
- Implement conversational unlock logic (Prompt Engineering focus).
- Implement second-stage persuasion analysis.
- Configuration: hardcoded or simple LocalStorage settings.

### Phase 2: Enhancements (Future)
- Parent dashboard: whitelist/blacklist management, interception history.
- Multi-modal detection: AI Vision for image risk scanning.
- Age-tiered responses: different AI tone and depth for different age groups.

---

## Open Questions

1. **Exa AI Latency**: If Exa analysis exceeds 5 seconds, should we provide a "skip" option, or prioritize safety and make the user wait?
   - *Recommendation: Show fun loading knowledge tips, prioritize safety.*
2. **Whitelist Strategy**: Should commonly visited safe sites (e.g. google.com, youtube.com) skip scanning entirely, or always perform at least a quick check?
   - *Recommendation: Maintain a configurable whitelist with quick checks.*
---
## Our PPT 
https://www.canva.com/design/DAHCnrTrteg/raKKjzz7QhRYQgeb3TrtMA/edit?utm_content=DAHCnrTrteg&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton
--
## 👥 Team Members & Responsibilities

| Member | Role | Key Responsibilities |
|:------:|:----:|:---------------------|
| **Shirley** | Frontend Developer | • UI/UX design and development<br>• Frontend architecture planning |
| **Kelly** | Multimedia Designer | • Presentation design and creation<br>• Video editing and post-production |
| **Andrew** | Backend Developer | • Server-side logic development<br>• System architecture planning |
| **Shawn** | Backend Developer<br>+ Chrome Extension | • Backend feature development<br>• Chrome extension development|

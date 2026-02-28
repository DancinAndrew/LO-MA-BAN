# 🦊 ScoutNet - AI-Powered Online Safety Guide for Children

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Chrome Web Store](https://img.shields.io/badge/Chrome-Extension-blue.svg)](https://chrome.google.com/webstore)
[![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)](https://github.com/your-repo/scoutnet)

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

**ScoutNet** is a Chrome extension designed for children (targeting ages 8-14) that reimagines online safety. Unlike traditional parental control tools that rely on blocking and surveillance, ScoutNet takes a **privacy-first**, **guidance-based** approach.

By leveraging AI to analyze web content in real-time, we transform everyday browsing into opportunities for building digital literacy. When a potential risk is detected, the system pauses navigation and engages the child in a Socratic dialogue—guiding them to recognize threats themselves rather than simply blocking access. An emergency "Safety Button" ensures children can immediately seek help when feeling threatened.

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
| Age | under 18 years old |
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
| **FR-002** | URL Analysis | System extracts the URL and calls **Exa AI** to retrieve page content and risk context. |
| **FR-003** | Risk Assessment | - **Safe**: Overlay fades out, normal browsing resumes. Green shield icon appears in corner.<br>- **Risky**: Overlay remains, enters conversational guidance mode. |

### 4.2. Conversational Guidance Mode

This is ScoutNet's core differentiator—turning blocking into education.

| Feature ID | Description | Details |
|------------|-------------|---------|
| **FR-004** | Risk Scenario Generation | Calls **FeatherAI (Qwen)** to generate age-appropriate warnings and guiding questions based on Exa AI's analysis. |
| **FR-005** | Interactive Overlay | Screen remains blurred. A dialogue box appears asking contextual questions:<br>• Phishing: "This site asks for your parents' credit card. Why do you think it needs this?"<br>• Violent content: "The people in this video are doing dangerous things. What might happen if you copy them?" |
| **FR-006** | Unlock Logic | Child must answer the question. AI evaluates response:<br>• **Pass**: "Great job! You recognized this is a trick." Overlay fades, warning icon remains in corner.<br>• **Fail**: AI explains further, may ask again or suggest leaving. |

### 4.3. Safety Button (SOS)

An emergency mechanism initiated by the child.

| Feature ID | Description | Details |
|------------|-------------|---------|
| **FR-007** | Trigger Mechanism | A prominent button floats on the browser extension bar or page sidebar. For situations like cyberbullying, harassment, or disturbing content. |
| **FR-008** | Auto-capture & Notification | Click captures current browser screen (including URL). Sends screenshot with preset message (e.g., "I need help here.") to designated parent/guardian email. |
| **FR-009** | Post-trigger Feedback | Screen shows supportive message: "Help is on the way. Don't worry, we're here with you." |

---

## User Flow

### Complete Interaction Flow

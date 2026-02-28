"""
SecurityCheckerService — async multi-source threat intelligence.
Uses httpx.AsyncClient + asyncio.gather for parallel API calls.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import Settings

logger = logging.getLogger(__name__)


def _base64_url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


class SecurityCheckerService:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self.timeout = settings.api_timeout

    async def _check_virustotal(
        self, client: httpx.AsyncClient, target_url: str
    ) -> dict[str, Any]:
        if not self._s.virustotal_api_key:
            return {"source": "virustotal", "available": False, "reason": "API key not configured"}
        try:
            url_id = _base64_url_id(target_url)
            resp = await client.get(
                f"{self._s.virustotal_base_url}/urls/{url_id}",
                headers={"x-apikey": self._s.virustotal_api_key, "Accept": "application/json"},
            )
            if resp.status_code == 404:
                return {"source": "virustotal", "available": True, "found": False,
                        "message": "URL not found in VirusTotal database"}
            if resp.status_code == 200:
                attrs = resp.json().get("data", {}).get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                mal = stats.get("malicious", 0)
                sus = stats.get("suspicious", 0)
                if mal > 3 or (mal + sus) > 5:
                    risk = "critical"
                elif mal > 0 or sus > 2:
                    risk = "warning"
                elif sus > 0:
                    risk = "caution"
                else:
                    risk = "safe"
                return {
                    "source": "virustotal", "available": True, "found": True,
                    "risk_level": risk, "stats": stats,
                    "categories": attrs.get("categories", []),
                    "reputation": attrs.get("reputation", 0),
                    "last_analysis_date": attrs.get("last_analysis_date"),
                    "details": {"malicious": mal, "suspicious": sus,
                                "harmless": stats.get("harmless", 0),
                                "undetected": stats.get("undetected", 0)},
                }
            logger.error("VirusTotal API %s: %s", resp.status_code, resp.text[:200])
            return {"source": "virustotal", "available": True,
                    "error": f"HTTP {resp.status_code}", "message": resp.text[:200]}
        except Exception as exc:
            logger.error("VirusTotal request failed: %s", exc)
            return {"source": "virustotal", "available": False, "error": str(exc)}

    async def _check_urlhaus(
        self, client: httpx.AsyncClient, target_url: str
    ) -> dict[str, Any]:
        if not self._s.urlhaus_auth_key:
            return {"source": "urlhaus", "available": False, "reason": "Auth-Key not configured"}
        try:
            resp = await client.post(
                "https://urlhaus-api.abuse.ch/v1/url/",
                data={"url": target_url.strip().rstrip("/"), "format": "json"},
                headers={"Auth-Key": self._s.urlhaus_auth_key,
                         "User-Agent": "ScamAnalyzer/2.0", "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("query_status")
                if status == "no_results":
                    return {"source": "urlhaus", "available": True, "found": False,
                            "message": "URL not listed in URLhaus database"}
                if status == "ok" and data.get("url_info"):
                    info = data["url_info"]
                    return {
                        "source": "urlhaus", "available": True, "found": True,
                        "risk_level": "critical",
                        "threat_type": info.get("threat"),
                        "tags": info.get("tags", []),
                        "date_added": info.get("date_added"),
                        "reporter": info.get("reporter"),
                        "details": {"host": info.get("host"),
                                    "status": info.get("url_status"),
                                    "blacklists": info.get("blacklists", {})},
                    }
                return {"source": "urlhaus", "available": True, "found": False, "query_status": status}
            return {"source": "urlhaus", "available": True, "found": False,
                    "http_status": resp.status_code, "error_detail": resp.text[:100]}
        except Exception as exc:
            logger.error("URLhaus request failed: %s", exc)
            return {"source": "urlhaus", "available": False, "error": str(exc)}

    async def _check_phishtank(
        self, client: httpx.AsyncClient, target_url: str
    ) -> dict[str, Any]:
        try:
            encoded = base64.urlsafe_b64encode(target_url.encode()).decode().rstrip("=")
            resp = await client.post(
                "https://api.phishtank.com/v2/phishtank/verify",
                data={"url": encoded, "format": "json"},
                headers={"User-Agent": "ScamAnalyzer/2.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results", [{}])[0].get("in_database") == "true":
                    return {"source": "phishtank", "available": True, "found": True,
                            "risk_level": "critical",
                            "phish_id": data["results"][0].get("phish_id")}
                return {"source": "phishtank", "available": True, "found": False}
            return {"source": "phishtank", "available": True, "found": False,
                    "http_status": resp.status_code}
        except Exception as exc:
            return {"source": "phishtank", "available": False, "error": str(exc)}

    async def _check_google_safebrowsing(
        self, client: httpx.AsyncClient, target_url: str
    ) -> dict[str, Any]:
        if not self._s.google_safe_browsing_api_key:
            return {"source": "google_safebrowsing", "available": False,
                    "reason": "API key not configured"}
        try:
            payload = {
                "client": {"clientId": "scamanalyzer", "clientVersion": "2.0.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING",
                                    "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": target_url.strip()}],
                },
            }
            resp = await client.post(
                "https://safebrowsing.googleapis.com/v4/threatMatches:find",
                params={"key": self._s.google_safe_browsing_api_key},
                json=payload,
                headers={"Content-Type": "application/json",
                         "User-Agent": "ScamAnalyzer/2.0"},
            )
            if resp.status_code == 200:
                matches = resp.json().get("matches", [])
                if matches:
                    threats = [{"threat_type": m.get("threatType"),
                                "platform": m.get("platformType"),
                                "cache_duration": m.get("cacheDuration")} for m in matches]
                    return {"source": "google_safebrowsing", "available": True,
                            "found": True, "risk_level": "critical",
                            "threats": threats, "match_count": len(matches), "details": matches}
                return {"source": "google_safebrowsing", "available": True, "found": False,
                        "message": "No threats found in Google Safe Browsing database"}
            logger.error("Google SB HTTP %s: %s", resp.status_code, resp.text[:200])
            return {"source": "google_safebrowsing", "available": True,
                    "error": f"HTTP {resp.status_code}",
                    "details": resp.text[:200]}
        except Exception as exc:
            logger.error("Google Safe Browsing failed: %s", exc)
            return {"source": "google_safebrowsing", "available": False, "error": str(exc)}

    @staticmethod
    def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
        weights = {"critical": 3, "warning": 2, "caution": 1, "safe": 0}
        total_score = 0
        checked = 0
        critical_flags: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for r in results:
            if not r.get("available"):
                continue
            checked += 1
            risk = r.get("risk_level", "safe")
            total_score += weights.get(risk, 0)
            if risk == "critical":
                critical_flags.append({
                    "source": r["source"],
                    "threat_type": r.get("threat_type") or r.get("categories"),
                    "details": r.get("details", {}),
                })
            elif risk in ("warning", "caution"):
                warnings.append({"source": r["source"],
                                 "reason": r.get("message") or r.get("stats")})

        if checked == 0:
            overall, confidence = "inconclusive", "low"
        elif total_score >= 6 or len(critical_flags) >= 2:
            overall = "critical"
            confidence = "high" if checked >= 3 else "medium"
        elif total_score >= 3 or len(critical_flags) >= 1:
            overall, confidence = "high", "medium"
        elif total_score >= 1:
            overall, confidence = "medium", "medium"
        else:
            overall, confidence = "low", "high"

        return {
            "overall_risk": overall,
            "confidence": confidence,
            "risk_score": min(total_score * 25, 100),
            "checked_sources": checked,
            "critical_flags": critical_flags,
            "warnings": warnings,
            "raw_results": results,
        }

    async def check_all(self, target_url: str) -> dict[str, Any]:
        logger.info("Security check started: %s", target_url)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            results = await asyncio.gather(
                self._check_virustotal(client, target_url),
                self._check_urlhaus(client, target_url),
                self._check_phishtank(client, target_url),
                self._check_google_safebrowsing(client, target_url),
            )
        aggregated = self._aggregate(list(results))
        aggregated["target_url"] = target_url
        aggregated["timestamp"] = datetime.now(timezone.utc).isoformat()
        logger.info("Security check done — risk: %s", aggregated["overall_risk"])
        return aggregated

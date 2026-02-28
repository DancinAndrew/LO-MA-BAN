#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security API Client: 整合多個威脅情報平台 API
- VirusTotal
- URLhaus
- PhishTank
- Google Safe Browsing (可選)
"""
import base64
import hashlib
import requests
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from config import Config

logger = logging.getLogger(__name__)

def base64_url_encode(url: str) -> str:
    """將 URL 進行 base64 URL-safe 編碼（移除 padding）"""
    encoded = base64.urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')
    return encoded.rstrip('=')

def sha256_hash_url(url: str) -> str:
    """計算 URL 的 SHA256 hash（用於 Google Safe Browsing）"""
    return hashlib.sha256(url.encode('utf-8')).hexdigest().lower()

class SecurityAPIClient:
    """整合多個安全平台 API 的客戶端"""
    
    def __init__(self):
        self.timeout = Config.API_TIMEOUT
        self.results = {}
        
    def check_virustotal(self, target_url: str) -> Dict:
        """
        呼叫 VirusTotal API v3
        需要先將 URL base64 encode 後作為 ID
        """
        if not Config.VIRUSTOTAL_API_KEY:
            logger.warning("⚠️ 未設定 VIRUSTOTAL_API_KEY，跳過 VirusTotal 檢查")
            return {"source": "virustotal", "available": False, "reason": "API key not configured"}
        
        try:
            url_id = base64_url_encode(target_url)
            endpoint = f"{Config.VIRUSTOTAL_BASE_URL}/urls/{url_id}"
            
            headers = {
                "x-apikey": Config.VIRUSTOTAL_API_KEY,
                "Accept": "application/json"
            }
            
            response = requests.get(endpoint, headers=headers, timeout=self.timeout)
            
            if response.status_code == 404:
                return {
                    "source": "virustotal",
                    "available": True,
                    "found": False,
                    "message": "URL not found in VirusTotal database"
                }
            elif response.status_code == 200:
                data = response.json()
                attributes = data.get('data', {}).get('attributes', {})
                stats = attributes.get('last_analysis_stats', {})
                
                # 計算風險指標
                malicious = stats.get('malicious', 0)
                suspicious = stats.get('suspicious', 0)
                harmless = stats.get('harmless', 0)
                total = malicious + suspicious + harmless
                
                risk_level = "safe"
                if malicious > 3 or (malicious + suspicious) > 5:
                    risk_level = "critical"
                elif malicious > 0 or suspicious > 2:
                    risk_level = "warning"
                elif suspicious > 0:
                    risk_level = "caution"
                
                return {
                    "source": "virustotal",
                    "available": True,
                    "found": True,
                    "risk_level": risk_level,
                    "stats": stats,
                    "categories": attributes.get('categories', []),
                    "reputation": attributes.get('reputation', 0),
                    "last_analysis_date": attributes.get('last_analysis_date'),
                    "details": {
                        "malicious": malicious,
                        "suspicious": suspicious,
                        "harmless": harmless,
                        "undetected": stats.get('undetected', 0)
                    }
                }
            else:
                logger.error(f"VirusTotal API error: {response.status_code} - {response.text}")
                return {
                    "source": "virustotal",
                    "available": True,
                    "error": f"HTTP {response.status_code}",
                    "message": response.text[:200]
                }
                
        except requests.RequestException as e:
            logger.error(f"VirusTotal request failed: {e}")
            return {"source": "virustotal", "available": False, "error": str(e)}
    
    def check_urlhaus(self, target_url: str) -> Dict:
        """
        URLhaus API - 需要 Auth-Key（免費註冊）
        https://urlhaus.abuse.ch/api/
        """
        if not Config.URLHAUS_AUTH_KEY:
            logger.warning("⚠️ 未設定 URLHAUS_AUTH_KEY，跳過 URLhaus 檢查")
            return {"source": "urlhaus", "available": False, "reason": "Auth-Key not configured"}
        
        try:
            endpoint = "https://urlhaus-api.abuse.ch/v1/url/"
            
            # ✅ 清理輸入
            target_url = target_url.strip().rstrip('/')
            
            # ✅ POST 請求 + form data
            payload = {"url": target_url, "format": "json"}
            
            # ✅ 關鍵：Auth-Key 放在 header
            headers = {
                "Auth-Key": Config.URLHAUS_AUTH_KEY,  # ← 新增認證
                "User-Agent": "ScamAnalyzer/1.0",
                "Accept": "application/json"
            }
            
            response = requests.post(
                endpoint,
                data=payload,  # form-encoded, not JSON
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                query_status = data.get('query_status')
                
                if query_status == 'no_results':
                    return {
                        "source": "urlhaus",
                        "available": True,
                        "found": False,
                        "message": "URL not listed in URLhaus database"
                    }
                elif query_status == 'ok' and data.get('url_info'):
                    url_info = data['url_info']
                    return {
                        "source": "urlhaus",
                        "available": True,
                        "found": True,
                        "risk_level": "critical",  # URLhaus 只收錄惡意 URL
                        "threat_type": url_info.get('threat'),
                        "tags": url_info.get('tags', []),
                        "date_added": url_info.get('date_added'),
                        "reporter": url_info.get('reporter'),
                        "details": {
                            "host": url_info.get('host'),
                            "status": url_info.get('url_status'),
                            "blacklists": url_info.get('blacklists', {})
                        }
                    }
                else:
                    return {
                        "source": "urlhaus",
                        "available": True,
                        "found": False,
                        "query_status": query_status
                    }
            else:
                logger.warning(f"URLhaus HTTP {response.status_code}: {response.text[:200]}")
                return {
                    "source": "urlhaus",
                    "available": True,
                    "found": False,
                    "http_status": response.status_code,
                    "error_detail": response.text[:100]
                }
                
        except requests.RequestException as e:
            logger.error(f"URLhaus request failed: {e}")
            return {"source": "urlhaus", "available": False, "error": str(e)}
        except Exception as e:
            logger.error(f"URLhaus unexpected error: {e}")
            return {"source": "urlhaus", "available": False, "error": f"Unexpected: {e}"}
    
    def check_phishtank(self, target_url: str) -> Dict:
        """PhishTank - 注意：免費 API 功能有限，建議作為輔助"""
        try:
            # ✅ 正確端點（PhishTank API v2）
            endpoint = "https://api.phishtank.com/v2/phishtank/verify"
            
            # PhishTank 免費 API 需要 base64 + 特殊格式
            encoded_url = base64.urlsafe_b64encode(target_url.encode()).decode().rstrip('=')
            
            payload = {
                "url": encoded_url,
                "format": "json"
            }
            
            # ✅ 免費版不需要 API key，但功能受限
            headers = {"User-Agent": "ScamAnalyzer/1.0"}
            
            response = requests.post(endpoint, data=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                # PhishTank 回應結構
                if data.get('results', [{}])[0].get('in_database') == 'true':
                    return {
                        "source": "phishtank",
                        "available": True,
                        "found": True,
                        "risk_level": "critical",
                        "phish_id": data['results'][0].get('phish_id')
                    }
                return {"source": "phishtank", "available": True, "found": False}
            return {"source": "phishtank", "available": True, "found": False, "http_status": response.status_code}
        except Exception as e:
            return {"source": "phishtank", "available": False, "error": str(e)}
    
    def check_google_safebrowsing(self, target_url: str) -> Dict:
        """
        Google Safe Browsing API v4 - 需要 GCP 專案 + 啟用 Safe Browsing API
        https://developers.google.com/safe-browsing/v4/reference/rest/v4/threatMatches/find
        """
        if not Config.GOOGLE_SAFE_BROWSING_API_KEY:
            logger.warning("⚠️ 未設定 GOOGLE_SAFE_BROWSING_API_KEY，跳過檢查")
            return {"source": "google_safebrowsing", "available": False, "reason": "API key not configured"}
        
        try:
            # ✅ 正確端點：threatMatches:find
            endpoint = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
            
            payload = {
                "client": {
                    "clientId": "scamanalyzer",
                    "clientVersion": "1.0.0"
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE", 
                        "SOCIAL_ENGINEERING", 
                        "UNWANTED_SOFTWARE", 
                        "POTENTIALLY_HARMFUL_APPLICATION"
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": target_url.strip()}]  # ✅ 清理 URL
                }
            }
            
            # ✅ API Key 作為 query parameter
            params = {"key": Config.GOOGLE_SAFE_BROWSING_API_KEY}
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ScamAnalyzer/1.0"
            }
            
            logger.debug(f"📡 Google SB Request: {endpoint} | URL: {target_url}")
            
            response = requests.post(
                endpoint, 
                json=payload, 
                params=params, 
                headers=headers,
                timeout=self.timeout
            )
            
            logger.debug(f"📥 Google SB Response: {response.status_code} | {response.text[:200]}")
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                if matches:
                    threats = []
                    for match in matches:
                        threats.append({
                            "threat_type": match.get('threatType'),
                            "platform": match.get('platformType'),
                            "cache_duration": match.get('cacheDuration')
                        })
                    
                    logger.info(f"🚨 Google SB 偵測到 {len(matches)} 項威脅")
                    return {
                        "source": "google_safebrowsing",
                        "available": True,
                        "found": True,
                        "risk_level": "critical",
                        "threats": threats,
                        "match_count": len(matches),
                        "details": matches
                    }
                else:
                    logger.info("✅ Google SB 未發現威脅")
                    return {
                        "source": "google_safebrowsing",
                        "available": True,
                        "found": False,
                        "message": "No threats found in Google Safe Browsing database"
                    }
            elif response.status_code == 400:
                logger.error(f"Google SB 400 Bad Request: {response.text}")
                return {"source": "google_safebrowsing", "available": True, "error": "Bad Request", "details": response.text[:200]}
            elif response.status_code == 403:
                logger.error("Google SB 403 Forbidden - 檢查 API Key 是否有效且已啟用 Safe Browsing API")
                return {"source": "google_safebrowsing", "available": True, "error": "Forbidden - Check API Key & API enabled"}
            elif response.status_code == 404:
                logger.error(f"Google SB 404 - 端點錯誤或資源不存在: {response.text}")
                return {"source": "google_safebrowsing", "available": True, "error": "Endpoint not found - Check API version"}
            else:
                logger.warning(f"Google SB HTTP {response.status_code}: {response.text[:200]}")
                return {"source": "google_safebrowsing", "available": True, "error": f"HTTP {response.status_code}", "details": response.text[:100]}
                
        except requests.RequestException as e:
            logger.error(f"Google Safe Browsing request failed: {e}")
            return {"source": "google_safebrowsing", "available": False, "error": f"Request failed: {e}"}
        except Exception as e:
            logger.error(f"Google Safe Browsing unexpected error: {e}")
            return {"source": "google_safebrowsing", "available": False, "error": f"Unexpected: {e}"}
    
    def aggregate_results(self, results: List[Dict]) -> Dict:
        """
        整合所有 API 結果，計算整體風險評估
        """
        # 風險權重：critical=3, warning=2, caution=1, safe=0
        risk_weights = {"critical": 3, "warning": 2, "caution": 1, "safe": 0}
        
        total_score = 0
        checked_sources = 0
        critical_flags = []
        warnings = []
        
        for result in results:
            if not result.get('available'):
                continue
            checked_sources += 1
            
            risk = result.get('risk_level', 'safe')
            if risk in risk_weights:
                total_score += risk_weights[risk]
            
            if risk == 'critical':
                critical_flags.append({
                    "source": result['source'],
                    "threat_type": result.get('threat_type') or result.get('categories'),
                    "details": result.get('details', {})
                })
            elif risk in ['warning', 'caution']:
                warnings.append({
                    "source": result['source'],
                    "reason": result.get('message') or result.get('stats')
                })
        
        # 計算綜合風險等級
        if checked_sources == 0:
            overall_risk = "inconclusive"
            confidence = "low"
        elif total_score >= 6 or len(critical_flags) >= 2:
            overall_risk = "critical"
            confidence = "high" if checked_sources >= 3 else "medium"
        elif total_score >= 3 or len(critical_flags) >= 1:
            overall_risk = "high"
            confidence = "medium"
        elif total_score >= 1:
            overall_risk = "medium"
            confidence = "medium"
        else:
            overall_risk = "low"
            confidence = "high"
        
        return {
            "overall_risk": overall_risk,
            "confidence": confidence,
            "risk_score": min(total_score * 25, 100),  # 轉換為 0-100 分數
            "checked_sources": checked_sources,
            "critical_flags": critical_flags,
            "warnings": warnings,
            "raw_results": results
        }
    
    def check_all(self, target_url: str) -> Dict:
        """
        執行所有安全平台檢查並返回整合結果
        """
        logger.info(f"🔍 開始檢查目標網址: {target_url}")
        
        results = []
        
        # 依序呼叫各 API（可並行優化）
        results.append(self.check_virustotal(target_url))
        results.append(self.check_urlhaus(target_url))
        results.append(self.check_phishtank(target_url))
        results.append(self.check_google_safebrowsing(target_url))
        
        # 整合結果
        aggregated = self.aggregate_results(results)
        aggregated['target_url'] = target_url
        aggregated['timestamp'] = json.dumps({"$date": str(__import__('datetime').datetime.now())})
        
        logger.info(f"✅ 檢查完成，整體風險: {aggregated['overall_risk']}")
        return aggregated
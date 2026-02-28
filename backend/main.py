#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scam Analyzer v2 - 直接呼叫安全平台 API + Featherless AI 深度分析
支援：VirusTotal, URLhaus, PhishTank, Google Safe Browsing
"""
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ✅ 確保 .env 被載入
load_dotenv()

from config import Config
from security_api_client import SecurityAPIClient
from featherless_analyzer import FeatherlessAnalyzer
from report_generator import ReportGenerator
from utils import save_json, step_marker, load_json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Scam Analyzer v2: 安全平台 API + Featherless AI 深度分析'
    )
    parser.add_argument('url', nargs='?', help='要分析的目標網址')
    parser.add_argument('-o', '--output-dir', help='輸出資料夾（預設：./output）')
    parser.add_argument('--skip-llm', action='store_true', 
                       help='只執行安全 API 檢查，不呼叫 LLM')
    parser.add_argument('--llm-only', action='store_true',
                       help='跳過安全 API，使用現有 01_security_check.json 呼叫 LLM')
    parser.add_argument('--report-only', action='store_true',
                       help='僅從現有結果生成 Markdown 報告')
    parser.add_argument('--force-llm', action='store_true',
                       help='強制呼叫 LLM（即使風險等級低）')
    args = parser.parse_args()
    
    # ========== 目標網址 ==========
    target_url = args.url or Config.DEFAULT_TARGET_URL
    if not target_url:
        logger.error("❌ 請提供目標網址或設定 DEFAULT_TARGET_URL")
        sys.exit(1)
    
    target_url = target_url.strip()
    
    # ========== 輸出目錄 ==========
    output_dir = Path(args.output_dir) if args.output_dir else Config.setup_output_dir()
    Config.OUTPUT_DIR = output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("🔍 Scam Analyzer v2 - 安全平台 API + Featherless AI")
    logger.info("=" * 60)
    logger.info(f"🎯 目標網址：{target_url}")
    logger.info(f"📁 輸出目錄：{output_dir}")
    logger.info("=" * 60)
    
    try:
        # ========== Step 1: 安全平台 API 檢查 ==========
        security_output = output_dir / "01_security_check.json"
        
        if args.report_only or (args.llm_only and security_output.exists()):
            logger.info(step_marker(1, "使用現有安全檢查結果", "done"))
            security_results = load_json(security_output)
        else:
            logger.info(step_marker(1, "執行安全平台 API 檢查"))
            client = SecurityAPIClient()
            security_results = client.check_all(target_url)
            save_json(security_results, security_output)
            logger.info(step_marker(1, "安全檢查完成", "done"))
        
        # 如果只需要安全檢查結果，到此結束
        if args.skip_llm and not args.force_llm:
            print("\n" + "=" * 60)
            print("✅ 安全檢查結果摘要")
            print("=" * 60)
            print(f"🎯 目標：{target_url}")
            print(f"🚨 整體風險：{security_results['overall_risk'].upper()}")
            print(f"📊 信心程度：{security_results.get('confidence', 'unknown')}")
            print(f"🔢 風險分數：{security_results.get('risk_score', 'N/A')}/100")
            print(f"📡 已檢查來源：{security_results.get('checked_sources', 0)}")
            
            if security_results.get('critical_flags'):
                print("\n🚨 關鍵警告:")
                for flag in security_results['critical_flags'][:3]:
                    print(f"  - {flag['source']}: {flag.get('threat_type', '未知威脅')}")
            
            print(f"\n💾 完整結果：{security_output}")
            print("=" * 60)
            return
        
        # ========== Step 2: LLM 深度分析 ==========
        llm_output = output_dir / "02_llm_analysis.json"
        overall_risk = security_results.get('overall_risk', 'inconclusive')
        
        # 決定是否呼叫 LLM
        should_call_llm = (
            args.force_llm or 
            overall_risk in ['critical', 'high', 'medium'] or
            not args.skip_llm
        )
        
        if should_call_llm:
            logger.info(step_marker(2, f"風險等級：{overall_risk}，開始 LLM 深度分析"))
            
            analyzer = FeatherlessAnalyzer()
            llm_analysis = analyzer.analyze(target_url, security_results)
            
            # 合併結果
            final_result = {
                "target_url": target_url,
                "security_check": security_results,
                "llm_analysis": llm_analysis,
                "final_risk_level": llm_analysis.get('risk_level', overall_risk),
                "timestamp": datetime.now().isoformat()
            }
            
            save_json(final_result, llm_output)
            logger.info(step_marker(2, "LLM 分析完成", "done"))
        else:
            logger.info(step_marker(2, f"風險等級低 ({overall_risk})，跳過 LLM 分析", "done"))
            final_result = {
                "target_url": target_url,
                "security_check": security_results,
                "final_risk_level": overall_risk,
                "llm_analysis": None,
                "timestamp": datetime.now().isoformat()
            }
            save_json(final_result, llm_output)
        
        # ========== Step 3: 生成 Markdown 報告 ==========
        report_output = output_dir / "03_final_report.json"
        logger.info(step_marker(3, "生成 Markdown 報告"))
        
        # 使用 ReportGenerator（適配新資料結構）
        analysis_data = final_result.get('llm_analysis') or security_results
        cleaned_results = security_results.get('raw_results', [])
        
        generator = ReportGenerator(
            target_url=target_url,
            analysis_result=analysis_data,
            cleaned_results=cleaned_results
        )
        generator.generate_report(report_output)
        
        # ========== 輸出摘要 ==========
        print("\n" + "=" * 60)
        print("📋 分析結果摘要")
        print("=" * 60)
        print(f"🎯 目標：{target_url}")
        print(f"🚨 風險等級：{final_result['final_risk_level'].upper()}")
        
        if final_result.get('llm_analysis'):
            llm = final_result['llm_analysis']
            print(f"💡 威脅摘要：{llm.get('threat_summary', 'N/A')}")
            print(f"📝 建議：{llm.get('recommendations', ['無'])[:2]}")
            if llm.get('fallback_mode'):
                print("⚠️ 注意：LLM 分析使用降級模式（API 呼叫失敗）")
        
        print(f"\n💾 完整報告：{report_output}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ 用戶中斷執行")
        sys.exit(130)
    except Exception as e:
        logger.error(step_marker(0, f"執行失敗：{e}", "error"), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
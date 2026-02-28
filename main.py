#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scam Analyzer - 從 Exa 查詢到 Featherless 分析的完整流程
每步驟自動產出 JSON 檔案，最終生成 Markdown 報告
"""
import sys
import json
import logging
import argparse
from pathlib import Path
import requests

from config import Config
from exa_query import ExaQuery
from prompt_builder import PromptBuilder
from report_generator import generate_report_from_json
from utils import save_json, step_marker, load_json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Scam Analyzer: 每步驟產出 JSON + Markdown 報告')
    parser.add_argument('url', nargs='?', help='要分析的目標網址')
    parser.add_argument('-o', '--output-dir', help='輸出資料夾（預設：./output）')
    parser.add_argument('--skip-exa', action='store_true', help='跳過 Exa 查詢，使用現有 01_exa_raw.json')
    parser.add_argument('--skip-featherless', action='store_true', help='只建構 prompt，不呼叫 Featherless API')
    parser.add_argument('--report-only', action='store_true', help='僅從現有結果生成報告')
    
    args = parser.parse_args()
    target_url = args.url or Config.DEFAULT_TARGET_URL
    
    if not target_url:
        logger.error("請提供目標網址或設定 DEFAULT_TARGET_URL")
        sys.exit(1)
    
    # 設定輸出目錄
    output_dir = Path(args.output_dir) if args.output_dir else Config.setup_output_dir()
    Config.OUTPUT_DIR = output_dir
    
    # 驗證設定
    errors = Config.validate()
    if errors and not args.report_only:
        logger.error("設定錯誤:\n" + "\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    
    try:
        # ========== Step 1: Exa 查詢 ==========
        exa_output = output_dir / "01_exa_raw.json"
        if args.report_only or (args.skip_exa and exa_output.exists()):
            logger.info(step_marker(1, "使用現有 Exa 結果", "done"))
            exa_results = load_json(exa_output)
        else:
            exa = ExaQuery()
            exa_results = exa.search_and_save(target_url, output_path=exa_output)
        
        # ========== Step 2: 清理結果 ==========
        cleaned_output = output_dir / "02_cleaned_results.json"
        builder = PromptBuilder()
        cleaned_results = builder.clean_and_save_results(exa_results, output_path=cleaned_output)
        
        # ========== Step 3: 建構 Prompt ==========
        prompt_output = output_dir / "03_featherless_prompt.json"
        payload = builder.build_and_save_prompt(
            target_url, 
            cleaned_results, 
            output_path=prompt_output
        )
        
        # ========== Step 4: 呼叫 Featherless ==========
        result_output = output_dir / "04_analysis_result.json"
        if args.skip_featherless:
            logger.info(step_marker(4, "跳過 Featherless 呼叫（dry-run）", "done"))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            logger.info(step_marker(4, "呼叫 Featherless API"))
            response = requests.post(
                Config.FEATHERLESS_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {Config.FEATHERLESS_API_KEY}"
                },
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            analysis_result = response.json()
            
            # 儲存最終結果
            save_json(analysis_result, result_output)
            logger.info(step_marker(4, "分析完成", "done"))
        
        # ========== Step 5: 生成 Markdown 報告 ==========
        report_output = output_dir / "05_final_report.md"
        logger.info(step_marker(5, "生成 Markdown 報告"))
        generate_report_from_json(
            target_url,
            result_output,
            cleaned_output,
            report_output
        )
        logger.info(step_marker(5, "報告生成完成", "done"))
        
        # 輸出報告預覽
        print("\n" + "="*60)
        print("📄 報告預覽")
        print("="*60)
        report_content = report_output.read_text(encoding='utf-8')
        print(report_content[:2000] + "..." if len(report_content) > 2000 else report_content)
        print("="*60)
        print(f"✅ 完整報告已儲存至：{report_output}")
            
    except Exception as e:
        logger.error(step_marker(0, f"執行失敗：{e}", "error"), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
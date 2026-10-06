#!/usr/bin/env python3
"""
scripts/refresh_pipeline.py — Automated Data Freshness & Re-indexing Pipeline
=============================================================================
Orchestrates live portal scrapers (Notices, Datesheets, Announcements),
validates data integrity, and triggers atomic FAISS vector database rebuilding.

Usage:
    python3 scripts/refresh_pipeline.py             # Run one-shot update
    python3 scripts/refresh_pipeline.py --daemon    # Run continuous periodic refresh (every 6 hours)
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(ROOT_DIR, "data", "pipeline.log"), encoding="utf-8")
    ]
)

STATUS_FILE = os.path.join(ROOT_DIR, "data", "last_refresh.json")

def run_scraper(name: str, func) -> int:
    logging.info(f"🚀 [Pipeline] Running {name}...")
    try:
        items = func()
        count = len(items)
        logging.info(f"✅ [Pipeline] {name} completed successfully: {count} items.")
        return count
    except Exception as e:
        logging.error(f"❌ [Pipeline] {name} failed: {e}", exc_info=True)
        return 0

def run_refresh_cycle() -> dict:
    start_time = time.time()
    logging.info("==================================================")
    logging.info("🔄 Starting GNDEC RAG Data Refresh & Re-index Cycle")
    logging.info("==================================================")

    # 1. Scrape Notices
    from scripts.scrape_notices import scrape_gndec_notices, OUTPUT_FILE as NOTICES_OUT
    notices_count = 0
    try:
        notices = scrape_gndec_notices()
        notices_count = len(notices)
        with open(NOTICES_OUT, "w", encoding="utf-8") as f:
            json.dump(notices, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved {notices_count} notices to {NOTICES_OUT}")
    except Exception as e:
        logging.error(f"Failed to scrape notices: {e}")

    # 2. Scrape Datesheets
    from scripts.scrape_datesheets import scrape_datesheets, OUTPUT_FILE as DATESHEETS_OUT
    datesheets_count = 0
    try:
        datesheets = scrape_datesheets()
        datesheets_count = len(datesheets)
        with open(DATESHEETS_OUT, "w", encoding="utf-8") as f:
            json.dump(datesheets, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Saved {datesheets_count} datesheets to {DATESHEETS_OUT}")
    except Exception as e:
        logging.error(f"Failed to scrape datesheets: {e}")

    # 3. Trigger Atomic Vector DB Rebuild
    logging.info("🧠 Rebuilding FAISS vector index with atomic swap...")
    from backend.build_vector_db import build_faiss_index
    try:
        build_faiss_index()
        db_status = "success"
    except Exception as e:
        logging.error(f"Vector DB rebuild failed: {e}", exc_info=True)
        db_status = f"failed: {e}"

    elapsed = round(time.time() - start_time, 2)
    summary = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "notices_count": notices_count,
        "datesheets_count": datesheets_count,
        "vector_db_status": db_status
    }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logging.info(f"🎉 Pipeline cycle finished in {elapsed}s | Summary: {summary}")
    return summary

def main():
    parser = argparse.ArgumentParser(description="GNDEC RAG Automated Data Freshness Pipeline")
    parser.add_argument("--daemon", action="store_true", help="Run continuously on interval")
    parser.add_argument("--interval", type=int, default=21600, help="Refresh interval in seconds (default: 6h / 21600s)")
    args = parser.parse_args()

    if args.daemon:
        logging.info(f"🕒 Running in daemon mode. Refreshing every {args.interval} seconds.")
        while True:
            try:
                run_refresh_cycle()
            except Exception as e:
                logging.error(f"Unexpected error in refresh cycle: {e}")
            logging.info(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
    else:
        run_refresh_cycle()

if __name__ == "__main__":
    main()

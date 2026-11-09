import os
import json
import logging
import requests
import pdfplumber
import io

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
TNP_URL = "https://www.tnpgndec.com/files/Placement_Brochure_2026.pdf"

def extract_tables():
    logger.info("Downloading Placement Brochure to extract tables...")
    try:
        resp = requests.get(TNP_URL, verify=False, timeout=20)
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            all_tables_text = []
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    
                    # Convert table to markdown
                    md_table = ""
                    for row_idx, row in enumerate(table):
                        # Clean up None values and newlines in cells
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        md_table += "| " + " | ".join(clean_row) + " |\n"
                        if row_idx == 0: # Add separator after header
                            md_table += "|" + "|".join(["---"] * len(clean_row)) + "|\n"
                            
                    if "Discipline" in md_table or "Eligible" in md_table or "Package" in md_table or "Offers" in md_table:
                        q = "What are the exact placement statistics, job offers, eligible students, and packages for each branch or discipline at GNDEC?"
                        all_tables_text.append({
                            "question": q,
                            "answer": md_table,
                            "section": "Placement Statistics Table",
                            "source_file": "extract_tnp_tables",
                            "doc_url": TNP_URL
                        })
                        
            if all_tables_text:
                path = os.path.join(DATA_DIR, "tnp_data.json")
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                data.extend(all_tables_text)
                
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Successfully extracted and appended {len(all_tables_text)} placement tables to tnp_data.json!")
            else:
                logger.warning("No placement statistics table found in the PDF.")
                
    except Exception as e:
        logger.error(f"Failed to extract tables: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    extract_tables()

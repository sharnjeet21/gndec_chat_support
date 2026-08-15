import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://gndec.ac.in/faculty/"

def fetch_faculty_data():
    logger.info(f"Fetching main faculty directory at {BASE_URL}")
    try:
        resp = requests.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {BASE_URL}: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Extract department links (they contain '?deptt=')
    department_links = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if '?deptt=' in href:
            dept_name = a.text.strip()
            if dept_name and href not in [link['url'] for link in department_links]:
                # Build absolute url just in case
                abs_url = urljoin(BASE_URL, href)
                department_links.append({"name": dept_name, "url": abs_url})
    
    logger.info(f"Found {len(department_links)} departments.")
    
    all_faculty = []
    
    # Fetch faculty per department
    for dept in department_links:
        dept_name = dept['name']
        dept_url = dept['url']
        logger.info(f"Fetching faculty for department: {dept_name}")
        
        try:
            dept_resp = requests.get(dept_url, timeout=15)
            dept_resp.raise_for_status()
            dept_soup = BeautifulSoup(dept_resp.text, 'html.parser')
            
            tables = dept_soup.find_all('table')
            if not tables:
                logger.warning(f"No tables found for {dept_name}")
                continue
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    cols_text = [col.text.strip() for col in cols]
                    
                    if not cols_text or len(cols_text) < 3:
                        continue
                    
                    if 'Name' in cols_text[0] and 'Designation' in cols_text[1]:
                        continue
                        
                    name = " ".join(cols_text[0].split())
                    if not name or name.lower() == 'add faculty' or name.lower() == 'update faculty':
                        continue
                        
                    designation = cols_text[1] if len(cols_text) > 1 else ""
                    designation = " ".join(designation.split())
                    
                    email = cols_text[2] if len(cols_text) > 2 else ""
                    email = " ".join(email.split())
                    
                    faculty_member = {
                        "department": dept_name,
                        "name": name,
                        "designation": designation,
                        "email": email,
                    }
                    all_faculty.append(faculty_member)
                    
        except Exception as e:
            logger.error(f"Failed to fetch department {dept_name}: {e}")
            
    return all_faculty

if __name__ == "__main__":
    faculty_data = fetch_faculty_data()
    logger.info(f"Total faculty members scraped: {len(faculty_data)}")
    
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "faculty.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(faculty_data, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Saved faculty data to {out_path}")

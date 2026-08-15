import json
import requests
from bs4 import BeautifulSoup
import os

URL = 'https://admission.gndec.ac.in/Fee_Structure.php'
programs = [
    'B.Tech.',
    'MBA/MCA',
    'M.Tech.',
    'BBA/BCA',
    'B.VoC. (Interior Design)',
    'B.Arch.',
    'B.Com.(Entrepreneurship)',
    'B.Tech. - Lateral Entry'
]

results = []

for prog in programs:
    payload = {
        'program_dropdown': prog,
        'fee_structure_show': 'fee_structure_show',
        'submit': ''
    }
    r = requests.post(URL, data=payload, verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    md_table = ""
    for table in soup.find_all('table'):
        if 'Sr No.' in table.text:
            rows = table.find_all('tr')
            
            # Find the index of the header row that starts with 'Sr No.'
            start_idx = 0
            for i, row in enumerate(rows):
                if 'Sr No.' in row.text:
                    start_idx = i
                    break
            
            # The actual data rows are from start_idx + 1 onwards
            data_rows = rows[start_idx+1:]
            
            md_lines = []
            md_lines.append("| Sr No. | Program | Sem | Hostel (Boys) | Hostel (Girls) | PMS (Total) | PMS (Hostel Boys) | PMS (Hostel Girls) | TFW (Total) | TFW (Hostel Boys) | TFW (Hostel Girls) | Gen (Total) | Gen (Hostel Boys) | Gen (Hostel Girls) |")
            md_lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
            
            for tr in data_rows:
                cells = [c.text.strip().replace('\n', ' ').replace('\r', '') for c in tr.find_all(['td', 'th'])]
                if len(cells) >= 14: # some rows might be notes
                    # ensure we only take the first 14 if there are more, or pad if less
                    row_data = cells[:14]
                    md_lines.append("| " + " | ".join(row_data) + " |")
                    
            md_table = "\n".join(md_lines)
            break
            
    if md_table:
        results.append({
            'question': f'What is the detailed fee structure for {prog}?',
            'answer': f'The exact detailed fee structure for {prog} is:\n\n{md_table}\n\nNote: This is the official fee structure table. All values are in Rupees.',
            'section': 'Admissions & Fees',
            'source_file': 'admission.gndec.ac.in/Fee_Structure.php',
            'doc_url': 'https://admission.gndec.ac.in/Fee_Structure.php'
        })

HERE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
path = os.path.join(HERE, 'data', 'fee_structures.json')
with open(path, 'w') as f:
    json.dump(results, f, indent=2)
print(f'Saved perfectly formatted Markdown tables to {path}')

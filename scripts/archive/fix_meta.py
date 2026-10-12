import json

with open("backend/faiss_store/meta.json", "r") as f:
    data = json.load(f)

new_header = "| Sr No. | Name of Program | Semester | Hostel Fee Boys | Hostel Fee Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"

count = 0
for item in data:
    if "question" in item and "fee structure for" in item["question"].lower():
        ans = item.get("answer", "")
        if "| Sr No. | Program | Sem |" in ans:
            lines = ans.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if line.startswith("| Sr No. | Program | Sem |"):
                    new_lines.append(new_header)
                    skip = True
                elif skip and line.startswith("|---|---|---|"):
                    skip = False
                else:
                    if not skip:
                        new_lines.append(line)
            item["answer"] = "\n".join(new_lines)
            count += 1

with open("backend/faiss_store/meta.json", "w") as f:
    json.dump(data, f)

print(f"Updated {count} fee structure chunks in meta.json")

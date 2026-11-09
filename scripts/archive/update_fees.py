import json

with open("data/fee_structures.json", "r") as f:
    data = json.load(f)

# The new header
new_header = "| Sr No. | Name of Program | Semester | Hostel Fee Boys | Hostel Fee Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls | Total Semester Fee | Total Fee Hostlers Boys | Total Fee Hostlers Girls |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"

for item in data:
    ans = item["answer"]
    # We want to replace the existing markdown header
    # with the new_header
    lines = ans.split("\n")
    new_lines = []
    skip = False
    replaced = False
    for line in lines:
        if line.startswith("| Sr No. | Program | Sem |"):
            new_lines.append(new_header)
            skip = True
            replaced = True
        elif skip and line.startswith("|---|---|---|"):
            skip = False
        else:
            if not skip:
                new_lines.append(line)
    
    item["answer"] = "\n".join(new_lines)

with open("data/fee_structures.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated fee_structures.json")

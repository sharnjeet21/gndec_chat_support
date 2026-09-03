import re

with open("data/rag_evaluation_results.txt", "r") as f:
    content = f.read()

# Split by the separator
blocks = content.split("-" * 80 + "\n")

cleaned_blocks = []
for block in blocks:
    if not block.strip():
        continue
    if "Status: success" in block:
        cleaned_blocks.append(block + "-" * 80 + "\n")

with open("data/rag_evaluation_results_clean.txt", "w") as f:
    for block in cleaned_blocks:
        f.write(block)

print(f"Original blocks: {len(blocks) - 1}")
print(f"Cleaned blocks: {len(cleaned_blocks)}")

import sys
import os
import subprocess

if len(sys.argv) < 2:
    print("Usage: update_readme_link.py <url>")
    sys.exit(1)

new_url = sys.argv[1]
repo_dir = "/home/sharnjeet-singh/Developer/gndec_rag"

def update_readme_content():
    with open('README.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    out_lines = []
    in_live_link = False
    found_live_link = False
    
    for line in lines:
        if line.strip() == '## Live Link':
            in_live_link = True
            found_live_link = True
            out_lines.append(line)
            out_lines.append(f"\n[Click here to access the live agent]({new_url})\n\n")
            continue
            
        if in_live_link:
            if line.startswith('## ') or line.startswith('---'):
                in_live_link = False
                out_lines.append(line)
            continue
            
        if not in_live_link:
            out_lines.append(line)
            
    if not found_live_link:
        # Find where to insert it. After <div align="center"> block.
        for i, line in enumerate(out_lines):
            if '</div>' in line:
                out_lines.insert(i + 1, f"\n## Live Link\n[Click here to access the live agent]({new_url})\n\n")
                break
                
    with open('README.md', 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

def update_branches():
    # Save current branch
    res = subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True, text=True, cwd=repo_dir)
    original_branch = res.stdout.strip()
    
    # Get all local branches
    res = subprocess.run("git branch --format='%(refname:short)'", shell=True, capture_output=True, text=True, cwd=repo_dir)
    branches = res.stdout.strip().split('\n')
    
    for branch in branches:
        if not branch: continue
        print(f"Updating branch {branch}")
        subprocess.run(f"git checkout {branch}", shell=True, cwd=repo_dir)
        subprocess.run(f"git pull origin {branch}", shell=True, cwd=repo_dir)
        
        update_readme_content()
        
        # Commit and push
        subprocess.run("git add README.md", shell=True, cwd=repo_dir)
        res = subprocess.run("git diff --staged --quiet", shell=True, cwd=repo_dir)
        if res.returncode != 0: # Changes exist
            subprocess.run(["git", "commit", "-m", "Automated: Update Live Link in README on boot"], cwd=repo_dir)
            subprocess.run(f"git push origin {branch}", shell=True, cwd=repo_dir)
            
    # Restore original branch
    subprocess.run(f"git checkout {original_branch}", shell=True, cwd=repo_dir)

if __name__ == "__main__":
    update_branches()

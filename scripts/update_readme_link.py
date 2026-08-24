import sys
import os
import subprocess

if len(sys.argv) < 2:
    print("Usage: update_readme_link.py <url>")
    sys.exit(1)

new_url = sys.argv[1]
repo_dir = "/home/sharnjeet-singh/Developer/gndec_rag"

def update_readme_content():
    if not os.path.exists('README.md'):
        print("README.md not found in this branch. Skipping.")
        return False
        
    with open('README.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    out_lines = []
    in_live_link = False
    found_live_link = False
    
    for line in lines:
        # Update logo if present
        if "Guru_Nanak_Dev_Engineering_College_logo.png" in line:
            line = line.replace("https://upload.wikimedia.org/wikipedia/en/3/30/Guru_Nanak_Dev_Engineering_College_logo.png", "https://gndec.ac.in/sites/default/logo.png")
            
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
    return True

def update_development_branch():
    target_branch = "development"
    print(f"Checking out {target_branch}...")
    subprocess.run(f"git checkout {target_branch}", shell=True, cwd=repo_dir)
    subprocess.run(f"git pull origin {target_branch}", shell=True, cwd=repo_dir)
    
    print(f"Updating branch: {target_branch}")
    
    updated = update_readme_content()
    
    if updated:
        subprocess.run("git add README.md", shell=True, cwd=repo_dir)
        res = subprocess.run("git diff --staged --quiet", shell=True, cwd=repo_dir)
        if res.returncode != 0: # Changes exist
            subprocess.run(["git", "commit", "-m", f"Automated: Update Live Link in README on {target_branch}"], cwd=repo_dir)
        
        print(f"Pushing to origin {target_branch}...")
        push_res = subprocess.run(f"git push origin {target_branch}", shell=True, cwd=repo_dir, capture_output=True, text=True)
        print(push_res.stdout)
        if push_res.stderr:
            print("Error/Warning during push:", push_res.stderr)

if __name__ == "__main__":
    update_development_branch()


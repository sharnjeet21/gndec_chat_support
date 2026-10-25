#!/usr/bin/env bash

# Go to the project directory
cd /home/sharnjeet-singh/Developer/gndec_rag

# Load environment variables if needed
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Backend and Databases are now managed entirely by Docker using --restart always
# They will automatically start on boot.

# 2. Start the Frontend if not already running
if ! ss -tulpn | grep -q ":5173\b"; then
    echo "Starting frontend on port 5173..."
    cd support_ui
    nohup npm run dev > ../frontend_startup.log 2>&1 &
    cd ..
    sleep 10
else
    echo "Frontend is already running on port 5173."
fi

# 3. Start Cloudflare Tunnel pointing to frontend
rm -f cloudflare_startup.log
./cloudflared tunnel --url http://localhost:5173 > cloudflare_startup.log 2>&1 &
CF_PID=$!

# 4. Wait for Cloudflare to generate the link
CF_URL=""
for i in {1..30}; do
    CF_URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare.com' cloudflare_startup.log | head -n 1)
    if [ -n "$CF_URL" ]; then
        break
    fi
    sleep 1
done

if [ -n "$CF_URL" ]; then
    echo "Generated Cloudflare URL: $CF_URL"
    # Update README on all branches
    .venv/bin/python scripts/update_readme_link.py "$CF_URL" >> update_readme.log 2>&1
    # Send email
    .venv/bin/python scripts/send_mail.py "$CF_URL"
    # Keep running while cloudflared is alive
    wait $CF_PID
else
    echo "Error: Could not extract Cloudflare URL."
    kill $CF_PID 2>/dev/null || true
    exit 1
fi

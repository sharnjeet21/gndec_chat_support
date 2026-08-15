#!/usr/bin/env bash

# Go to the project directory
cd /home/sharnjeet-singh/Developer/gndec_rag

# Load environment variables if needed
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Backend and Databases are now managed entirely by Docker using --restart always
# They will automatically start on boot.

# 2. Start the Frontend
cd support_ui
nohup npm run dev > ../frontend_startup.log 2>&1 &
cd ..

# 3. Wait for services to start
sleep 15

# 4. Start Cloudflare Tunnel pointing to frontend
# Using nohup to keep it running
rm -f cloudflare_startup.log
nohup ./cloudflared tunnel --url http://localhost:5173 > cloudflare_startup.log 2>&1 &

# 5. Wait for Cloudflare to generate the link
sleep 10

# 6. Extract the URL
CF_URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare.com' cloudflare_startup.log | head -n 1)

if [ -n "$CF_URL" ]; then
    echo "Generated Cloudflare URL: $CF_URL"
    # Send email
    .venv/bin/python scripts/send_mail.py "$CF_URL"
else
    echo "Error: Could not extract Cloudflare URL."
fi

#!/bin/bash
# Must be run with sudo

# 1. Install Docker Compose if it's missing
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.29.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 2. Build and start all services (postgres, redis, backend web API)
# The docker-compose.yml already contains 'restart: always' so they will come up on boot.
echo "Building and starting all Docker services..."
docker-compose up -d --build

# 3. Add the user to the docker group so they don't need sudo in the future
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker "$SUDO_USER"
    echo "Added $SUDO_USER to the docker group."
    echo "Please log out and log back in (or reboot) for this to take effect."
fi

echo "All done! Your backend and databases are now running in Docker."

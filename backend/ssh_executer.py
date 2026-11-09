# backend/ssh_executor.py
import paramiko
import logging

logging.basicConfig(level=logging.INFO)

ALLOWED_COMMANDS = {
    "memory_usage": "free -h",
    "cpu_usage": "top -bn1 | head -n 5",
    "disk_usage": "df -h",
    "ping_google": "ping -c 4 google.com",
}


import os

def run_ssh_command(command: str) -> str:
    if command not in ALLOWED_COMMANDS:
        raise ValueError("Command not allowed")

    real_cmd = ALLOWED_COMMANDS[command]
    
    ip = os.getenv("SSH_HOST", "127.0.0.1")
    user = os.getenv("SSH_USER", "admin")
    key_path = os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa")
    
    logging.info(f"SSH request: {ip} → {real_cmd}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, key_filename=key_path, timeout=5)

    stdin, stdout, stderr = client.exec_command(real_cmd)
    result = stdout.read().decode() + stderr.read().decode()
    client.close()

    return result.strip()

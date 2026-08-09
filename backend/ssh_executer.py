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


def run_ssh_command(ip: str, user: str, password: str, command: str) -> str:
    if command not in ALLOWED_COMMANDS:
        raise ValueError("Command not allowed")

    real_cmd = ALLOWED_COMMANDS[command]
    logging.info(f"SSH request: {ip} → {real_cmd}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password, timeout=5)

    stdin, stdout, stderr = client.exec_command(real_cmd)
    result = stdout.read().decode() + stderr.read().decode()
    client.close()

    return result.strip()

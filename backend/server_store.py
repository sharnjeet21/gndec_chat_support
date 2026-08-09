# backend/server_store.py
import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from typing import Optional, Dict, Any

from .db import pg_execute

SECRET_KEY = os.getenv("SECRET_KEY", "").encode()

BLOCK_SIZE = 32  # 256-bit AES


def encrypt_password(password: str) -> str:
    cif = AES.new(SECRET_KEY, AES.MODE_ECB)
    enc = cif.encrypt(pad(password.encode(), BLOCK_SIZE))
    return base64.b64encode(enc).decode()


def decrypt_password(enc_password: str) -> str:
    data = base64.b64decode(enc_password)
    cif = AES.new(SECRET_KEY, AES.MODE_ECB)
    dec = unpad(cif.decrypt(data), BLOCK_SIZE)
    return dec.decode()


async def get_user_servers(phone: str):
    rows = await asyncio.to_thread(
        pg_execute,
        "SELECT * FROM user_servers WHERE phone=%s",
        (phone,),
        fetch=True,
    )
    if not rows:
        return []

    servers = []
    for r in rows:
        servers.append(
            {
                "server_ip": r["server_ip"],
                "ssh_user": r["ssh_user"],
                "ssh_password": decrypt_password(r["ssh_password"]),
            }
        )

    return servers

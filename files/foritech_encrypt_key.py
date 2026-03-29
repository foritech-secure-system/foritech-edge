#!/usr/bin/env python3
"""
foritech_encrypt_key.py — P0.1 Key Hardening Tool
Encrypts a plaintext ML-DSA-65 private key with AES-256-GCM.

Usage:
    export FORITECH_KEY_PASSPHRASE="<strong-passphrase>"
    python3 foritech_encrypt_key.py /etc/foritech/keys/ml_dsa_priv.bin

What it does:
    1. Creates .bak backup of original
    2. Encrypts in-place with AES-256-GCM (PBKDF2, 200k iterations)
    3. Sets permissions to 600

Format: FTKENC1(7) + SALT(16) + NONCE(12) + CIPHERTEXT+TAG
"""

import os
import secrets
import shutil
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_MAGIC = b"FTKENC1"


def _derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_key_file(path: Path, passphrase: str) -> None:
    raw = path.read_bytes()

    if raw.startswith(_MAGIC):
        print(f"[SKIP] Already encrypted: {path}")
        return

    # Backup
    backup = path.with_suffix(".bin.bak")
    shutil.copy2(path, backup)
    backup.chmod(0o600)
    print(f"[OK]   Backup: {backup}")

    salt    = secrets.token_bytes(16)
    nonce   = secrets.token_bytes(12)
    aes_key = _derive_aes_key(passphrase, salt)
    ct      = AESGCM(aes_key).encrypt(nonce, raw, None)

    encrypted = _MAGIC + salt + nonce + ct
    path.write_bytes(encrypted)
    path.chmod(0o600)

    print(f"[OK]   Encrypted: {path}")
    print(f"[OK]   Size: {len(raw)}B → {len(encrypted)}B")
    print(f"[INFO] KDF: PBKDF2-SHA256, 200k iterations")


def verify_roundtrip(path: Path, passphrase: str) -> None:
    """Verify that decrypt(encrypt(key)) == original."""
    data = path.read_bytes()
    if not data.startswith(_MAGIC):
        print("[FAIL] Not encrypted")
        sys.exit(1)

    offset  = len(_MAGIC)
    salt    = data[offset:offset + 16]
    nonce   = data[offset + 16:offset + 28]
    ct      = data[offset + 28:]
    aes_key = _derive_aes_key(passphrase, salt)

    try:
        plaintext = AESGCM(aes_key).decrypt(nonce, ct, None)
        print(f"[OK]   Roundtrip verify OK ({len(plaintext)} bytes decrypted)")
    except Exception as e:
        print(f"[FAIL] Decrypt failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: foritech_encrypt_key.py <key_file>")
        print("       FORITECH_KEY_PASSPHRASE must be set")
        sys.exit(1)

    passphrase = os.environ.get("FORITECH_KEY_PASSPHRASE")
    if not passphrase:
        print("[FAIL] FORITECH_KEY_PASSPHRASE not set")
        sys.exit(1)

    if len(passphrase) < 20:
        print("[WARN] Passphrase is short — use 32+ random characters")

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[FAIL] File not found: {path}")
        sys.exit(1)

    encrypt_key_file(path, passphrase)
    verify_roundtrip(path, passphrase)
    print("[DONE] Key encrypted and verified.")

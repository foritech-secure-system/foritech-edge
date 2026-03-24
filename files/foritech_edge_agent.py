#!/usr/bin/env python3
# foritech_edge_agent.py
# Foritech Edge Agent v0.8 — Standalone
# "Produce data that can be proven — not trusted."
#
# Dependencies: oqs (liboqs-python), cryptography, requests
# NO foritech SDK — verification stays on server (paid service)

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import struct
import sys
import time
from pathlib import Path

BANNER = """
╔══════════════════════════════════════════════════════╗
║           FORITECH EDGE AGENT  v0.8                  ║
║      Post-Quantum Secure Telemetry Signing           ║
╚══════════════════════════════════════════════════════╝
"""

def _ok(msg):   print(f"  [OK-FORITECH] {msg}")
def _info(msg): print(f"  [..] {msg}")
def _fail(msg): print(f"  [FAIL] {msg}", file=sys.stderr)
def _warn(msg): print(f"  [WARN] {msg}")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "device_id":       None,
    "priv_key":        "/etc/foritech/keys/ml_dsa_priv.bin",
    "pub_key":         "/etc/foritech/keys/ml_dsa_pub.bin",
    "kyber_pub":       "/etc/foritech/keys/kyber768_pub.bin",
    "verify_endpoint": "https://verify.foritech.bg/verify",
    "interval":        30,
    "transport":       "http",
    "output_dir":      "/tmp/foritech_out",
}

def load_config(path=None):
    cfg = dict(DEFAULT_CONFIG)
    if path and Path(path).exists():
        cfg.update(json.loads(Path(path).read_text()))
    if os.environ.get("FORITECH_DEVICE_ID"):
        cfg["device_id"] = os.environ["FORITECH_DEVICE_ID"]
    if os.environ.get("FORITECH_VERIFY_ENDPOINT"):
        cfg["verify_endpoint"] = os.environ["FORITECH_VERIFY_ENDPOINT"]
    if not cfg["device_id"]:
        try:
            cfg["device_id"] = Path("/etc/machine-id").read_text().strip()
        except Exception:
            cfg["device_id"] = "unknown-device"
    return cfg

# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------

def load_keys(cfg):
    for key in ["priv_key", "pub_key", "kyber_pub"]:
        p = Path(cfg[key])
        if not p.exists():
            _fail(f"Key not found: {p}")
            sys.exit(1)
    return (
        Path(cfg["priv_key"]).read_bytes(),
        Path(cfg["pub_key"]).read_bytes(),
        Path(cfg["kyber_pub"]).read_bytes(),
    )

# ---------------------------------------------------------------------------
# Minimal signed container (STANDALONE — no foritech SDK)
#
# Layout: MAGIC(5) + VERSION(1) + HDR_LEN(4LE) + HEADER(JSON) +
#         PAY_LEN(4LE) + PAYLOAD + SIG_LEN(4LE) + ML-DSA-65 SIG
#
# Signing only — no encryption.
# Verification is server-side (paid Foritech service).
# ---------------------------------------------------------------------------

MAGIC   = b"FTECH"
VERSION = 1

def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def build_signed_container(payload: bytes, device_id: str, priv: bytes, pub: bytes) -> bytes:
    import oqs

    nonce     = secrets.token_bytes(12)
    timestamp = int(time.time())
    kid       = hashlib.sha256(pub).hexdigest()

    header_dict = {
        "v":          VERSION,
        "alg":        {"sig": "ML-DSA-65"},
        "kid":        kid,
        "device_id":  device_id,
        "timestamp":  timestamp,
        "nonce":      _b64(nonce),
        "sig_required": True,
        "signer_pub": _b64(pub),
    }
    header = json.dumps(header_dict, separators=(",", ":")).encode("utf-8")

    with oqs.Signature("ML-DSA-65", secret_key=priv) as signer:
        signature = signer.sign(header + payload)

    return (
        MAGIC +
        bytes([VERSION]) +
        struct.pack("<I", len(header))  + header +
        struct.pack("<I", len(payload)) + payload +
        struct.pack("<I", len(signature)) + signature
    )

# ---------------------------------------------------------------------------
# Telemetry (replace _read_sensor with real Modbus/GPIO reads)
# ---------------------------------------------------------------------------

def collect_telemetry(device_id: str) -> dict:
    return {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "uptime":    _read_uptime(),
        "status":    "ok",
    }

def _read_uptime() -> float:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except Exception:
        return 0.0

# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def send_container(container: bytes, cfg: dict) -> bool:
    if cfg.get("transport") == "http":
        return _send_http(container, cfg)
    return _send_file(container, cfg)

def _send_http(container: bytes, cfg: dict) -> bool:
    try:
        import requests
        resp = requests.post(
            cfg["verify_endpoint"],
            data=container,
            headers={"Content-Type": "application/octet-stream"},
            timeout=10,
        )
        if resp.status_code == 200:
            _ok(f"Verified → {cfg['verify_endpoint']} [{resp.status_code}]")
            return True
        _warn(f"Server returned {resp.status_code}: {resp.text[:80]}")
        return False
    except Exception as e:
        _warn(f"HTTP send failed: {e}")
        return False

def _send_file(container: bytes, cfg: dict) -> bool:
    try:
        out_dir = Path(cfg.get("output_dir", "/tmp/foritech_out"))
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = out_dir / f"telemetry_{int(time.time())}.ftech"
        fname.write_bytes(container)
        _ok(f"Container saved → {fname} ({len(container)} bytes)")
        return True
    except Exception as e:
        _warn(f"File save failed: {e}")
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(config_path=None):
    print(BANNER)

    cfg = load_config(config_path)
    _info(f"Device ID : {cfg['device_id']}")
    _info(f"Transport : {cfg['transport']}")
    _info(f"Endpoint  : {cfg['verify_endpoint']}")
    _info(f"Interval  : {cfg['interval']}s")
    print()

    try:
        import oqs  # noqa: F401
        _ok("liboqs (PQC) available")
    except ImportError:
        _fail("liboqs not available — pip install liboqs-python")
        sys.exit(1)

    _info("Loading cryptographic keys...")
    priv, pub, kyber_pub = load_keys(cfg)
    _ok(f"ML-DSA-65 keys loaded  (kid: {hashlib.sha256(pub).hexdigest()[:16]}...)")
    print()

    _ok("Edge Agent ready — starting telemetry loop")
    print("  " + "─" * 50)

    cycle = 0
    while True:
        cycle += 1
        try:
            telemetry = collect_telemetry(cfg["device_id"])
            payload   = json.dumps(telemetry).encode("utf-8")
            _info(f"Cycle {cycle} — signing telemetry...")
            container = build_signed_container(payload, cfg["device_id"], priv, pub)
            _ok(f"Signed ({len(container)} bytes)")
            send_container(container, cfg)
        except KeyboardInterrupt:
            print()
            _info("Shutting down.")
            sys.exit(0)
        except Exception as e:
            _fail(f"Cycle {cycle} error: {e}")
        time.sleep(cfg["interval"])

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)

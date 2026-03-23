# Foritech Edge Agent

**Post-Quantum Secure Telemetry Signing for Industrial IoT**

> "Produce data that can be proven — not trusted."

---

## What is it?

Foritech Edge Agent runs on industrial IoT devices and signs telemetry data using **ML-DSA-65** — a post-quantum cryptographic signature algorithm.

Every telemetry message becomes a cryptographically verifiable container.  
Verification happens on the Foritech server — proving the data is real and untampered.

```
Device (IoT2050, PLC, sensor)
  ↓
Foritech Edge Agent
  ↓  ML-DSA-65 signature
Signed .ftech container
  ↓  HTTP / MQTT
Foritech Verification Server  →  VERIFIED / REJECTED
```

---

## One-line install

```bash
curl -fsSL https://edge.forisec.eu/install.sh | bash
```

Tested on:
- Siemens IoT2050 (ARM64, Debian)
- Ubuntu 22.04 / 24.04 (x86_64)
- Raspberry Pi (ARM)

---

## What gets installed

```
/opt/foritech-edge/
  foritech_edge_agent.py   ← standalone agent
  venv/                    ← Python environment
  config.json              ← device configuration

/etc/foritech/keys/
  ml_dsa_priv.bin          ← ML-DSA-65 private key (stays on device)
  ml_dsa_pub.bin           ← ML-DSA-65 public key
  kyber768_pub.bin         ← ML-KEM-768 key

/etc/systemd/system/
  foritech-edge.service    ← auto-start on boot
```

---

## Requirements

- Python 3.11+
- liboqs-python (installed automatically)
- 50MB disk space
- Network access to verification endpoint

---

## Configuration

Edit `/opt/foritech-edge/config.json`:

```json
{
    "device_id": "my-device-001",
    "verify_endpoint": "https://verify.foritech.bg/verify",
    "interval": 30,
    "transport": "http"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `device_id` | auto (machine-id) | Unique device identifier |
| `verify_endpoint` | https://verify.foritech.bg/verify | Foritech verification server |
| `interval` | 30 | Seconds between telemetry cycles |
| `transport` | http | `http` or `file` |

---

## Service management

```bash
# Start
sudo systemctl start foritech-edge

# Status
sudo systemctl status foritech-edge

# Logs
journalctl -u foritech-edge -f

# Stop
sudo systemctl stop foritech-edge
```

---

## What you'll see

```
╔══════════════════════════════════════════════════════╗
║           FORITECH EDGE AGENT  v0.8                  ║
║      Post-Quantum Secure Telemetry Signing           ║
╚══════════════════════════════════════════════════════╝

  [..] Device ID : 6acd1ccb24c44a5ea287620e80a5c237
  [..] Transport : http
  [..] Endpoint  : https://verify.foritech.bg/verify
  [..] Interval  : 30s

  [OK-FORITECH] liboqs (PQC) available
  [OK-FORITECH] ML-DSA-65 keys loaded  (kid: 6e669d49c371bdad...)

  [OK-FORITECH] Edge Agent ready — starting telemetry loop
  ──────────────────────────────────────────────────
  [..] Cycle 1 — signing telemetry...
  [OK-FORITECH] Signed (6282 bytes)
  [OK-FORITECH] Verified → https://verify.foritech.bg/verify [200]
```

---

## Security model

- Private key **never leaves the device**
- Every message is signed with **ML-DSA-65** (post-quantum)
- Verification happens **server-side** — edge agent cannot verify itself
- Replay protection via nonce + timestamp
- KID derived from public key: `SHA256(pub_key).hex()`

---

## Add your own telemetry

Edit the `collect_telemetry()` function in `foritech_edge_agent.py`:

```python
def collect_telemetry(device_id: str) -> dict:
    return {
        "device_id":   device_id,
        "timestamp":   int(time.time()),
        "temperature": read_modbus_register(1),   # your sensor
        "pressure":    read_modbus_register(2),   # your sensor
        "status":      "ok",
    }
```

---

## Supported devices

| Device | Architecture | Status |
|--------|-------------|--------|
| Siemens IoT2050 | ARM64 | ✅ Tested |
| Raspberry Pi 4 | ARM64 | ✅ Compatible |
| Ubuntu Server | x86_64 | ✅ Tested |
| Docker container | any | ✅ Compatible |

---

## About Foritech

Foritech Secure System is a **post-quantum cryptographic verification platform** for telemetry and machine data.

> In a world where AI can fake anything, Foritech proves what is real.

- Website: [foritech.bg](https://foritech.bg)
- Verification API: [verify.foritech.bg](https://verify.foritech.bg)
- Edge installer: [edge.forisec.eu](https://edge.forisec.eu)

---

## License

Edge Agent is open source.  
Foritech Verification Engine is proprietary — [contact us](mailto:forrybg.hh@gmail.com) for licensing.

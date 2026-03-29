# FORITECH HARDENING STRATEGY — EDGE & REPLAY

## SUMMARY

- Edge is the weakest trust point → must be hardened first
- Replay protection must become persistent (Redis) ✅ DONE
- Timestamp window confirmed acceptable ✅ DONE
- Key storage hardened (AES-256-GCM) ✅ DONE
- Core remains untouched (pure, deterministic) ✅
- Goal: reach TRL 8 (enterprise-ready security)

---

## 1. EDGE HARDENING

### Goal
Prevent private key extraction.

### Status — 🟡 PHASE 1 COMPLETE / PHASE 2 PENDING

**Phase 1 — Completed (2026-03-29, commit 9f0a867)**

Implemented: Encrypted Key Storage

```
disk → AES-256-GCM encrypted ml_dsa_priv.bin
         ↓
systemd EnvironmentFile → FORITECH_KEY_PASSPHRASE
         ↓
PBKDF2-SHA256 (200k iter) → AES key
         ↓
AES-GCM decrypt → ML-DSA-65 key in RAM
         ↓
Sign
```

Files:
- `foritech_edge_agent.py` — patched `load_keys()` with decrypt logic
- `foritech_encrypt_key.py` — key encryption tool
- `/etc/foritech/edge.env` — passphrase (chmod 600, root only)

**Phase 2 — Planned**

TPM 2.0 seal/unseal (IoT2050 has TPM hardware):

```
disk → encrypted ML-DSA key
         ↓
TPM 2.0 → unseal AES key
         ↓
AES-GCM decrypt → ML-DSA key in RAM
         ↓
Sign
```

Note: Direct TPM signing not possible — ML-DSA-65 not supported in TPM yet.
TPM protects the AES key, not the ML-DSA key directly.

**Phase 3 — Future**

Remote signing (key never on device):
```
Device → unsigned payload → HSM/server → signed container
```

---

### Options Reference

| Option | Status | Notes |
|--------|--------|-------|
| A. Secure Element (TPM/HSM) | Phase 2 | Best — key never leaves hardware |
| B. Encrypted Key Storage | ✅ Done | Passphrase via systemd env |
| C. Remote Signing | Future | Enterprise tier feature |

---

## 2. REPLAY HARDENING

### Goal
Make replay impossible across restarts.

### Status — ✅ COMPLETE (confirmed 2026-03-29)

**Implementation:** Redis-backed RedisReplayGuard

- Store: `foritech:replay:{device_id}:{nonce}` with TTL=300s
- SET NX — atomic, no race conditions
- Persistent across service restarts
- Multi-process safe

**Root cause resolved:** orphan uvicorn process was holding port 8080,
causing foritech-verify.service to crash-loop 14865 times.
Service now stable.

---

## 3. TIMESTAMP HARDENING

### Goal
Minimize replay window.

### Status — ✅ ACCEPTABLE (2026-03-29)

**Current:** window=300s, consistent with nonce TTL.
Nonce is primary defense. Timestamp is secondary hint only.
No change required.

---

## 4. DEVICE CONTROL

### Status — ⏳ P1

Add:
- [ ] Device revocation list
- [ ] Key rotation
- [ ] Device identity tracking

---

## 5. TESTING HARDENING

### Status — ⏳ P1

Add tests:
- [ ] Restart replay attack (verify Redis persistence)
- [ ] Timestamp drift
- [ ] Key compromise simulation
- [ ] Encrypted key wrong passphrase → clean FAIL

---

## 6. DEPLOYMENT MODEL

### Phase 1 (✅ DONE — 2026-03-29)
- [x] Redis replay guard (persistent)
- [x] Encrypted key storage (AES-256-GCM)
- [x] systemd EnvironmentFile (passphrase injection)
- [x] Timestamp window confirmed acceptable

### Phase 2 (next)
- [ ] TPM 2.0 integration (IoT2050)
- [ ] Key rotation + revocation

### Phase 3 (future)
- [ ] Remote signing / HSM
- [ ] Enterprise key management

---

## BUSINESS POSITIONING

| Tier | Key Security | Feature Label |
|------|-------------|---------------|
| Starter | Software key | Basic signing |
| Industrial | Encrypted key (Phase 1) ✅ | Hardened device identity |
| Enterprise | TPM-backed (Phase 2) | Hardware-backed device identity |

DO NOT market Phase 1 as "secure key storage" to enterprise clients.
Market as: "hardened software storage — hardware-backed security available".

---

## FINAL PRINCIPLE

Edge = weakest point
Server = source of truth
Core = cryptographic truth engine

DO NOT move logic into core.

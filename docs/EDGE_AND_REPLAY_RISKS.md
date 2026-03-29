# FORITECH SECURITY RISKS — EDGE & REPLAY LAYER

## PURPOSE

Defines the highest-risk attack surfaces in Foritech architecture.
Focus: Edge + Service Layer (NOT core).

---

## CRITICAL CONTEXT

Core:
- deterministic
- no replay
- no time

Service layer:
- replay protection
- time validation

---

# 🔴 P0 RISKS

## 1. EDGE KEY MANAGEMENT

### Problem
Private key stored on disk:
```
/etc/foritech/keys/
```

### Risk
Physical access → key theft → valid signatures → full compromise

### Status — ✅ MITIGATED (2026-03-29, commit 9f0a867)

**Implementation:**
- `ml_dsa_priv.bin` encrypted with AES-256-GCM
- KDF: PBKDF2-SHA256, 200k iterations
- Passphrase injected via systemd `EnvironmentFile=/etc/foritech/edge.env` (chmod 600)
- `foritech_encrypt_key.py` — key encryption tool (roundtrip verified)
- Backward compat: plaintext keys accepted with WARN (transition period)

**Residual risk:**
- Passphrase stored on same device — not TPM-backed yet
- Memory scraping possible after decrypt (Python limitation)
- This is P1 mitigation, not full P0 elimination

**Next phase (Phase 2):**
- TPM 2.0 seal/unseal for AES key (IoT2050 has TPM)
- Remove passphrase from filesystem entirely

---

## 2. REPLAY GUARD (NON-PERSISTENT)

### Problem
InMemoryReplayGuard resets on restart

### Risk
Replay becomes valid after restart

### Status — ✅ RESOLVED (pre-existing, confirmed 2026-03-29)

**Implementation:**
- `RedisReplayGuard` active in `services/verification_api.py`
- Keys: `foritech:replay:{device_id}:{nonce}` with TTL
- Persistent across restarts
- Fallback to `InMemoryReplayGuard` only if Redis unavailable

**Root cause found:** `foritech-verify.service` was crash-looping (14865 restarts)
due to orphan uvicorn process holding port 8080.
Fixed by killing orphan + `systemctl restart foritech-verify.service`.

---

## 3. TIMESTAMP WINDOW

### Problem
Wide window allows replay

### Risk
Attacker replays within allowed time

### Status — ✅ ACCEPTABLE (confirmed 2026-03-29)

**Current config:** `window_seconds=300`

**Assessment:**
- Nonce is primary replay defense (SET NX in Redis)
- Timestamp is secondary check only
- 300s window is consistent with nonce TTL
- No change required

---

# SYSTEM RISK CHAIN

```
[Key compromise] → attacker can sign
+
[Replay weakness] → attacker can resend
+
[Wide time window] → system accepts
```

**Current state:** chain is broken at replay layer (Redis nonce) and partially
hardened at key layer (AES-GCM). Full break requires TPM (Phase 2).

---

# RULE

DO NOT FIX IN CORE.

Fix in:
- Edge
- Service layer

---

# ACTION PLAN

## P0 (✅ DONE — 2026-03-29)
- [x] Redis replay guard active and persistent
- [x] Timestamp window confirmed acceptable
- [x] Key encrypted (AES-256-GCM + PBKDF2)
- [x] systemd EnvironmentFile (chmod 600)
- [x] foritech_encrypt_key.py roundtrip verified

## P1 (short-term)
- [ ] Key rotation strategy
- [ ] Device revocation flow
- [ ] Replay attack tests (restart scenario)
- [ ] Rate limiter → Redis (currently in-memory)

## P2 (mid-term)
- [ ] TPM 2.0 seal/unseal for AES key (IoT2050 hardware)
- [ ] Hardware-backed signing (longer term)

---

# FINAL PRINCIPLE

Edge = weakest point
Server = source of truth
Core = cryptographic truth engine

DO NOT move logic into core.

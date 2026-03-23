# Foritech Edge Agent v0.8 — Session Notes
Date: 2026-03-23

## Какво беше направено

### Архитектурно решение
Edge Agent е standalone — без foritech SDK зависимост.
Verification остава на сървъра (платена услуга).

```
IoT2050 (edge)                    Сървър (платен)
──────────────────                ─────────────────
foritech_edge_agent.py            Foritech Core SDK
  oqs (ML-DSA-65)                 verify engine
  cryptography                    replay protection
  requests                        trust decisions
  ── NO foritech SDK ──            audit logs
```

### Файлове
- `foritech_edge_agent.py` — standalone агент
- `install.sh` — едноредова инсталация
- Публично достъпни на: `https://edge.forisec.eu/files/`

### Инсталация на ново устройство
```bash
curl -fsSL https://edge.forisec.eu/install.sh | bash
```

### Container формат (вграден в агента)
```
MAGIC(5) + VERSION(1) + HDR_LEN(4LE) + HEADER(JSON) +
PAY_LEN(4LE) + PAYLOAD + SIG_LEN(4LE) + ML-DSA-65 SIG
```
Signing only — без encryption. Verification е server-side.

---

## Тествано на IoT2050 ARM64

```
Device ID : 6acd1ccb24c44a5ea287620e80a5c237
Platform  : aarch64, Debian, Python 3.11.2
liboqs    : 0.15.0 (system) + liboqs-python 0.14.1

[OK-FORITECH] ML-DSA-65 keys loaded  (kid: 6e669d49c371bdad...)
[OK-FORITECH] Signed (6282 bytes)
[OK-FORITECH] Container saved → /tmp/foritech_out/telemetry_*.ftech
```

Забележка: 7 минути стартиране = oqs инициализация на ARM.
След инициализация — бързо и стабилно.

---

## Известни проблеми и бележки

### liboqs версия mismatch
```
UserWarning: liboqs version 0.15.0 differs from liboqs-python 0.14.1
```
Не блокира. Signing работи. Да се оправи при следващ update на liboqs-python.

### oqs пакет конфликт
На IoT2050 имаше два `oqs` пакета:
- `oqs` (expression parser) — грешен
- `liboqs-python` — правилният

Fix: `pip uninstall oqs && pip install liboqs-python`
Добавено в install.sh за следващата версия.

### Ключове
Ключовете се генерират от install.sh при инсталация.
Намират се в `/etc/foritech/keys/`.
Private key никога не напуска устройството.

---

## Следващи стъпки

### Агент
- [ ] Modbus четене от Schneider meter (реален sensor)
- [ ] MQTT transport (в момента само HTTP/file)
- [ ] Offline буфериране при липса на мрежа
- [ ] Hardware-backed keys (TPM)

### Сървър
- [ ] Verification endpoint за `.ftech` контейнери от агента
- [ ] Container format compatibility (агент vs SDK)
- [ ] Replay guard за агент containers

### Инфраструктура
- [ ] `install.sh` — fix oqs конфликт автоматично
- [ ] `install.sh` — добави liboqs build от source за ARM
- [ ] Версиониране на агента (`/files/v0.8/foritech_edge_agent.py`)

---

## Бизнес модел (от архитектурния документ)

Edge = pen (подписва) — open/limited
Server = court (решава истината) — closed/paid

Агентът може да е публичен.
Verification engine остава затворен.

Pricing:
- €0.001–0.01 / verification
- €5–20 / device / месец
- €50k–250k enterprise deployment

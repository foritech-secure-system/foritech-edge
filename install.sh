#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║           FORITECH EDGE INSTALLER  v0.8.1            ║"
echo "║      Post-Quantum Secure Telemetry Signing           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

INSTALL_DIR="/opt/foritech-edge"
KEY_DIR="/etc/foritech/keys"

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
echo "  [..] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-venv python3-pip curl git \
    cmake ninja-build libssl-dev > /dev/null
echo "  [OK-FORITECH] System dependencies installed"

# ---------------------------------------------------------------------------
# Device ID
# ---------------------------------------------------------------------------
DEVICE_ID=$(cat /etc/machine-id)
echo "  [OK-FORITECH] Device ID: $DEVICE_ID"

# ---------------------------------------------------------------------------
# Install directory
# ---------------------------------------------------------------------------
sudo mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# Download agent
# ---------------------------------------------------------------------------
echo "  [..] Downloading Foritech Edge Agent..."
sudo curl -fsSL https://edge.forisec.eu/files/foritech_edge_agent.py \
    -o foritech_edge_agent.py
echo "  [OK-FORITECH] Agent downloaded"

# ---------------------------------------------------------------------------
# Python venv
# ---------------------------------------------------------------------------
echo "  [..] Creating Python environment..."
sudo python3 -m venv venv
sudo venv/bin/pip install --upgrade pip --quiet
sudo venv/bin/pip install requests --quiet
echo "  [OK-FORITECH] Python environment ready"

# ---------------------------------------------------------------------------
# liboqs — build from source (required for ML-DSA-65)
# ---------------------------------------------------------------------------
echo "  [..] Building liboqs (post-quantum crypto)..."
echo "       This takes 2-5 minutes on first install..."

if [ ! -f /usr/local/lib/liboqs.so ]; then
    curl -fsSL https://edge.forisec.eu/liboqs-0.14.0.tar.gz -o /tmp/liboqs-0.14.0.tar.gz
    mkdir -p /tmp/liboqs-build
    tar -xzf /tmp/liboqs-0.14.0.tar.gz -C /tmp/liboqs-build --strip-components=1
    cmake -S /tmp/liboqs-build -B /tmp/liboqs-build/build \
        -GNinja \
        -DBUILD_SHARED_LIBS=ON \
        -DOQS_BUILD_ONLY_LIB=ON \
        -DCMAKE_BUILD_TYPE=Release \
        > /dev/null 2>&1
    cmake --build /tmp/liboqs-build/build > /dev/null 2>&1
    sudo cmake --install /tmp/liboqs-build/build > /dev/null 2>&1
    sudo ldconfig
    rm -rf /tmp/liboqs-build
    echo "  [OK-FORITECH] liboqs built and installed"
else
    echo "  [OK-FORITECH] liboqs already installed — skipping build"
fi

# ---------------------------------------------------------------------------
# liboqs-python — remove conflicting 'oqs' package if present
# ---------------------------------------------------------------------------
echo "  [..] Installing liboqs-python..."
sudo venv/bin/pip uninstall oqs -y 2>/dev/null || true
sudo venv/bin/pip install liboqs-python --quiet
echo "  [OK-FORITECH] liboqs-python installed"

# ---------------------------------------------------------------------------
# cryptography
# ---------------------------------------------------------------------------
sudo venv/bin/pip install "cryptography==46.0.5" --quiet
echo "  [OK-FORITECH] cryptography installed"

# ---------------------------------------------------------------------------
# Generate ML-DSA-65 + ML-KEM-768 keys
# ---------------------------------------------------------------------------
sudo mkdir -p "$KEY_DIR"

if [ ! -f "$KEY_DIR/ml_dsa_priv.bin" ]; then
    echo "  [..] Generating ML-DSA-65 keys..."
    sudo venv/bin/python3 - << 'PYEOF'
import oqs, os, pathlib

key_dir = pathlib.Path("/etc/foritech/keys")

# ML-DSA-65
with oqs.Signature("ML-DSA-65") as sig:
    pub = sig.generate_keypair()
    priv = sig.export_secret_key()
(key_dir / "ml_dsa_pub.bin").write_bytes(pub)
(key_dir / "ml_dsa_priv.bin").write_bytes(priv)
os.chmod(key_dir / "ml_dsa_priv.bin", 0o600)

# ML-KEM-768
with oqs.KeyEncapsulation("Kyber768") as kem:
    kyber_pub = kem.generate_keypair()
(key_dir / "kyber768_pub.bin").write_bytes(kyber_pub)

print("  [OK-FORITECH] ML-DSA-65 keys generated")
print("  [OK-FORITECH] ML-KEM-768 key generated")
PYEOF
else
    echo "  [OK-FORITECH] Keys already exist — skipping generation"
fi

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    sudo tee "$INSTALL_DIR/config.json" > /dev/null << CONFIG
{
    "device_id": "$DEVICE_ID",
    "priv_key": "$KEY_DIR/ml_dsa_priv.bin",
    "pub_key":  "$KEY_DIR/ml_dsa_pub.bin",
    "kyber_pub": "$KEY_DIR/kyber768_pub.bin",
    "verify_endpoint": "https://verify.foritech.bg/verify",
    "api_key": "a8f8c8410f67dbefb7c7b34fe1599fe90c4befd06d633fb1eb2713e9cdb0755d",
    "interval": 30,
    "transport": "http"
}
CONFIG
    echo "  [OK-FORITECH] Config created"
fi

# ---------------------------------------------------------------------------
# Systemd service
# ---------------------------------------------------------------------------
echo "  [..] Installing systemd service..."
sudo tee /etc/systemd/system/foritech-edge.service > /dev/null << SERVICE
[Unit]
Description=Foritech Edge Agent v0.8
After=network.target

[Service]
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/foritech_edge_agent.py $INSTALL_DIR/config.json
Environment=VIRTUAL_ENV=$INSTALL_DIR/venv
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable foritech-edge
echo "  [OK-FORITECH] Systemd service installed"

echo ""
echo "  ────────────────────────────────────────────────────"
echo "  [OK-FORITECH] Foritech Edge Agent installed successfully"
echo ""
echo "  Start:   sudo systemctl start foritech-edge"
echo "  Status:  sudo systemctl status foritech-edge"
echo "  Logs:    journalctl -u foritech-edge -f"
echo "  Config:  $INSTALL_DIR/config.json"
echo "  Keys:    $KEY_DIR/"
echo "  ────────────────────────────────────────────────────"

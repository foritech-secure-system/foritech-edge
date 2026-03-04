#!/bin/bash
set -e

echo "---------------------------------"
echo " Foritech Edge Installer"
echo "---------------------------------"

sudo apt update
sudo apt install -y python3 python3-venv git

cd /opt

if [ ! -d "foritech-edge-runtime" ]; then
    git clone https://github.com/forrybg/foritech-secure-system.git foritech-edge-runtime
fi

cd foritech-edge-runtime/foritech-edge

python3 -m venv venv
source venv/bin/activate

pip install .

echo ""
echo "Foritech Edge installed successfully."
echo ""
echo "Run:"
echo "foritech-edge --help"

#!/bin/bash
set -e

echo "---------------------------------"
echo " Foritech Edge Installer"
echo "---------------------------------"

sudo apt update
sudo apt install -y python3 python3-venv python3-pip

INSTALL_DIR="/opt/foritech-edge"

sudo mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip

pip install git+https://github.com/forrybg/foritech-secure-system.git#subdirectory=foritech-edge

echo ""
echo "Foritech Edge installed."
echo ""
echo "Run:"
echo "source /opt/foritech-edge/venv/bin/activate"
echo "foritech-edge --help"

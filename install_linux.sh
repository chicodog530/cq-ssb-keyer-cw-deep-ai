#!/bin/bash
set -e

echo "CQ Voice Keyer - Linux Installer"
echo "--------------------------------"

# Detect package manager and install hamlib (for rigctld) and python dependencies
if command -v apt-get >/dev/null 2>&1; then
    echo "Detected Debian/Ubuntu-based system."
    echo "Installing system dependencies (requires sudo)..."
    sudo apt-get update
    sudo apt-get install -y libhamlib-utils python3-venv python3-pip python3-dev portaudio19-dev libasound2-dev
elif command -v dnf >/dev/null 2>&1; then
    echo "Detected Fedora-based system."
    echo "Installing system dependencies (requires sudo)..."
    sudo dnf install -y hamlib portaudio-devel alsa-lib-devel python3-devel
elif command -v pacman >/dev/null 2>&1; then
    echo "Detected Arch-based system."
    echo "Installing system dependencies (requires sudo)..."
    sudo pacman -Sy --noconfirm hamlib portaudio alsa-lib python
else
    echo "Unsupported package manager."
    echo "Please manually install 'rigctld' (from hamlib) and portaudio development headers for python sounddevice."
fi

# Create virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv and install python requirements
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create a run script
echo "Creating run_linux.sh script..."
cat << 'EOF' > run_linux.sh
#!/bin/bash
# Move to the directory where the script is located
cd "$(dirname "$0")"
source venv/bin/activate
python3 main.py
EOF

chmod +x run_linux.sh

echo "--------------------------------"
echo "Installation complete!"
echo "You can now start the app by running: ./run_linux.sh"

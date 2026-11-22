#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Run once with sudo, after `make`:   sudo ./install.sh
# Installs the kernel program and a system service that starts at boot and keeps the program attached whenever the
# controller is connected, plus a launcher for the settings window (no root needed to use it).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run with sudo."; exit 1; }
USER_NAME="${SUDO_USER:?run it with sudo from your own account}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
HERE="$(cd "$(dirname "$0")" && pwd)"
for f in build/eb-loader build/eb.bpf.o; do
    [ -f "$HERE/$f" ] || { echo "$f is missing: run 'make' first."; exit 1; }
done

install -d -m 755 /usr/local/lib/elite-binds
install -m 755 "$HERE/build/eb-loader" "$HERE/elite_binds/service.py" /usr/local/lib/elite-binds/
install -m 644 "$HERE/build/eb.bpf.o" "$HERE/elite_binds/eb_common.py" /usr/local/lib/elite-binds/
mv /usr/local/lib/elite-binds/service.py /usr/local/lib/elite-binds/eb-service.py

cat > /etc/systemd/system/elite-binds-bpf.service <<UNIT
[Unit]
Description=Elite Binds: remap Xbox Elite paddles inside the kernel (HID-BPF)

[Service]
ExecStart=/usr/local/lib/elite-binds/eb-service.py --config $USER_HOME/.config/elite-binds/config.json
Restart=always
RestartSec=3
TimeoutStopSec=8

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now elite-binds-bpf.service

# launcher for the settings window, owned by the user
sudo -u "$USER_NAME" bash -c "
    mkdir -p '$USER_HOME/.local/bin' '$USER_HOME/.local/share/applications' '$USER_HOME/.config/elite-binds'
    chmod +x '$HERE/elite_binds/gui.py'
    ln -sf '$HERE/elite_binds/gui.py' '$USER_HOME/.local/bin/elite-binds-gui'
    cat > '$USER_HOME/.local/share/applications/elite-binds.desktop' <<D
[Desktop Entry]
Type=Application
Name=Elite Binds
Comment=Choose what the Xbox Elite back paddles do
Exec=$HERE/elite_binds/gui.py
Icon=input-gaming
Categories=Game;Settings;
Terminal=false
D
"
echo "Installed and started. Open 'Elite Binds' from your apps menu, or run: elite-binds-gui"
echo "Remove with: sudo $HERE/uninstall.sh"

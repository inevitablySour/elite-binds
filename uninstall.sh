#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run with sudo."; exit 1; }
USER_HOME="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"
systemctl disable --now elite-binds-bpf.service 2>/dev/null || true
rm -f /etc/systemd/system/elite-binds-bpf.service
rm -rf /usr/local/lib/elite-binds
systemctl daemon-reload
rm -f "$USER_HOME/.local/bin/elite-binds-gui" "$USER_HOME/.local/share/applications/elite-binds.desktop"
echo "Removed. The controller is back to plain xpadneo. Your settings in ~/.config/elite-binds were kept."

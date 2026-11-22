#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run with sudo."; exit 1; }
USER_HOME="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"

# stop the service first, so the kernel program is removed before its files are
systemctl stop elite-binds-bpf.service 2>/dev/null || true
systemctl disable elite-binds-bpf.service 2>/dev/null || true
# if anything is left (the loader keeps the program attached while it runs), stop it too
if pgrep -x eb-loader >/dev/null; then
    pkill -x eb-loader || true
    sleep 1
fi
if systemctl is-active --quiet elite-binds-bpf.service || pgrep -x eb-loader >/dev/null; then
    echo "The service or its loader is still running. Not removing files. Try: sudo systemctl kill elite-binds-bpf" >&2
    exit 1
fi

rm -f /etc/systemd/system/elite-binds-bpf.service
rm -rf /usr/local/lib/elite-binds /run/elite-binds
systemctl daemon-reload
rm -f "$USER_HOME/.local/bin/elite-binds-gui" "$USER_HOME/.local/share/applications/elite-binds.desktop"
echo "Stopped and removed. The controller is back to plain xpadneo. Your settings in ~/.config/elite-binds were kept."

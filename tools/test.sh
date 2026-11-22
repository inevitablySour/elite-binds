#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Run with sudo, and stop the elite-binds-bpf service first (sudo systemctl stop elite-binds-bpf).
# Temporary test: P1=A, P2=B, P3=X, P4=Y. Press Ctrl+C to remove it again.
set -e
dir="$(cd "$(dirname "$0")/.." && pwd)"
dev=$(ls -d /sys/bus/hid/devices/0005:045E:0B22.* 2>/dev/null | head -1)
[ -n "$dev" ] || { echo "Elite controller not connected over Bluetooth."; exit 1; }
id=$((16#${dev##*.}))
rules=$(mktemp)
printf '0 1 14 0x01 0\n1 1 14 0x02 0\n2 1 14 0x08 0\n3 1 14 0x10 0\n' > "$rules"
echo "hid id $id. P1=A, P2=B, P3=X, P4=Y. Check with a gamepad tester, then press Ctrl+C here to remove it."
exec "$dir/build/eb-loader" "$id" "$rules" "$dir/build/eb.bpf.o"

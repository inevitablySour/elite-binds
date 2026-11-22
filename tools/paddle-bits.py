#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run with sudo. Asks for each paddle in turn and shows byte 19 (paddle bits) and byte 14 (A/B/X/Y/LB/RB/View/Menu) while it is held.
Run it once with test.sh stopped (raw) and once with test.sh running (rewritten)."""
import glob, os, select, sys, time
dev = None
for d in glob.glob("/sys/bus/hid/devices/0005:045E:0B22.*"):
    for h in glob.glob(d + "/hidraw/hidraw*"):
        dev = "/dev/" + os.path.basename(h)
if not dev:
    sys.exit("Elite controller not found over Bluetooth.")
fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)

def drain():
    while select.select([fd], [], [], 0)[0]:
        os.read(fd, 256)

ASK = [("P1", "TOP-LEFT"), ("P2", "BOTTOM-LEFT"), ("P3", "TOP-RIGHT"), ("P4", "BOTTOM-RIGHT")]
for name, where in ASK:
    for attempt in range(3):
        drain()
        input(f"\nPress Enter, THEN press and release {name} ({where} paddle) once: ")
        seen = set()
        seen14 = set()
        end = time.time() + 4
        while time.time() < end:
            if select.select([fd], [], [], 0.3)[0]:
                data = os.read(fd, 256)
                if data[0] == 1 and len(data) >= 20:
                    if data[19] & 0x0f:
                        seen.add(data[19] & 0x0f)
                    if data[14]:
                        seen14.add(data[14])
        if seen or seen14:
            print(f"  {name} -> byte19 paddle bits: " + (", ".join(f"{v:04b}" for v in sorted(seen)) or "none") + "   byte14 buttons: " + (", ".join(f"{v:08b}" for v in sorted(seen14)) or "none"))
            break
        print("  nothing arrived, try again")
    else:
        print(f"  {name}: no signal at all")

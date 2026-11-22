#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run with sudo. Prints a line only when a button changes. Press, one at a time, holding ~1 s each, waiting ~1 s between:
A B X Y LB RB View Menu L3(press left stick) R3(press right stick) Xbox-button  D-pad up/down/left/right  LT RT  P1 P2 P3 P4
Say each name out loud/in order so the list can be matched. Ctrl+C to stop."""
import glob, os, select, sys

dev = None
for d in glob.glob("/sys/bus/hid/devices/0005:045E:0B22.*"):
    for h in glob.glob(d + "/hidraw/hidraw*"):
        dev = "/dev/" + os.path.basename(h)
if not dev:
    sys.exit("Elite controller (045E:0B22) not found over Bluetooth.")
fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
# bytes that hold buttons / d-pad / share / paddles. Sticks (1-8), triggers (9-12) and byte 18 (status, flickers) are ignored.
WATCH = [13, 14, 15, 16, 17, 19]
last = None
n = 0
print("ready - start pressing (A first)", flush=True)
try:
    while True:
        r, _, _ = select.select([fd], [], [], 1)
        if not r:
            continue
        data = os.read(fd, 256)
        if data[0] != 1 or len(data) < 20:
            continue
        cur = tuple(data[i] for i in WATCH)
        # triggers: show only when clearly pressed
        lt = data[9] | (data[10] << 8)
        rt = data[11] | (data[12] << 8)
        trig = (lt > 300, rt > 300)
        state = (cur, trig)
        if state != last:
            last = state
            n += 1
            print(f"{n:3d}: " + " ".join(f"b{i}={v:08b}" for i, v in zip(WATCH, cur)) + f"  LT={'ON' if trig[0] else '-'} RT={'ON' if trig[1] else '-'}  (LT={lt} RT={rt})", flush=True)
except KeyboardInterrupt:
    pass

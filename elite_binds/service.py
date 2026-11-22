#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Root service: keeps the paddle-remap kernel program attached to the Xbox Elite 2 (Bluetooth) while it is connected,
and keeps its rules in step with the user's Elite Binds settings file."""
import argparse
import glob
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from eb_common import rules_text  # noqa: E402

def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)

def find_hid():
    for d in sorted(glob.glob("/sys/bus/hid/devices/0005:045E:0B22.*")):
        return int(d.rsplit(".", 1)[1], 16)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--loader", default="/usr/local/lib/elite-binds/eb-loader")
    ap.add_argument("--object", default="/usr/local/lib/elite-binds/eb.bpf.o")
    ap.add_argument("--run-dir", default="/run/elite-binds")
    a = ap.parse_args()
    os.makedirs(a.run_dir, exist_ok=True)
    rules = os.path.join(a.run_dir, "rules.txt")
    status = os.path.join(a.run_dir, "status")
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))
    loader, attached, mtime = None, None, None

    def set_status(text):
        try:
            with open(status, "w") as f:
                f.write(text + "\n")
            os.chmod(status, 0o644)
        except OSError:
            pass

    def write_rules():
        with open(rules + ".tmp", "w") as f:
            f.write(rules_text(a.config))
        os.replace(rules + ".tmp", rules)

    def kill_loader():
        nonlocal loader, attached
        if loader and loader.poll() is None:
            loader.terminate()
            try:
                loader.wait(3)
            except subprocess.TimeoutExpired:
                loader.kill()
        loader, attached = None, None

    set_status("waiting for the controller")
    while not stop:
        hid = find_hid()
        if loader and loader.poll() is not None:
            log("loader exited, will retry")
            loader, attached = None, None
        if hid != attached and (loader or hid is None):
            kill_loader()
            set_status("waiting for the controller")
        if hid is not None and loader is None:
            write_rules()
            mtime = os.path.getmtime(a.config) if os.path.exists(a.config) else None
            loader = subprocess.Popen([a.loader, str(hid), rules, a.object])
            attached = hid
            log(f"attached to controller (hid id {hid})")
            set_status(f"active (hid id {hid})")
        if loader:
            try:
                m = os.path.getmtime(a.config)
            except OSError:
                m = None
            if m != mtime:
                mtime = m
                write_rules()
                loader.send_signal(signal.SIGHUP)
                log("settings changed, rules updated")
        time.sleep(1)
    kill_loader()
    set_status("stopped")

if __name__ == "__main__":
    main()

# SPDX-License-Identifier: GPL-2.0-only
"""Shared pieces: the paddle targets, and reading and writing the settings file."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "elite-binds"
CONFIG_FILE = CONFIG_DIR / "config.json"

PADDLES = ["P1", "P2", "P3", "P4"]  # bits 0 to 3 of byte 19 of the controller's input report
PADDLE_LABELS = {
    "P1": "P1 (top left)",
    "P2": "P2 (bottom left)",
    "P3": "P3 (top right)",
    "P4": "P4 (bottom right)",
}
NONE_NAME = "None (do nothing)"

# What a paddle can become: (type, byte, mask, hat value), in the controller's ORIGINAL report layout, which is
# what the kernel program sees before the xpadneo driver rearranges it.
#   type 1: set a button bit        type 2: a D-pad direction (hat value)
#   type 3: push a trigger fully in (byte is the first byte of its 16 bit value)
TARGETS = {
    NONE_NAME: None,
    "A": (1, 14, 0x01, 0),
    "B": (1, 14, 0x02, 0),
    "X": (1, 14, 0x08, 0),
    "Y": (1, 14, 0x10, 0),
    "LB (L1)": (1, 14, 0x40, 0),
    "RB (R1)": (1, 14, 0x80, 0),
    "LT (L2)": (3, 9, 0, 0),
    "RT (R2)": (3, 11, 0, 0),
    "Left stick click (L3)": (1, 15, 0x20, 0),
    "Right stick click (R3)": (1, 15, 0x40, 0),
    "View (Back)": (1, 16, 0x01, 0),
    "Menu (Start)": (1, 15, 0x08, 0),
    "Xbox button": (1, 15, 0x10, 0),
    "D-pad up": (2, 0, 0, 1),
    "D-pad right": (2, 0, 0, 3),
    "D-pad down": (2, 0, 0, 5),
    "D-pad left": (2, 0, 0, 7),
}


def default_config():
    return {"active": "default", "profiles": {"default": {p: NONE_NAME for p in PADDLES}}}


def load_config(path=CONFIG_FILE):
    try:
        cfg = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default_config()
    profiles = cfg.get("profiles") if isinstance(cfg, dict) else None
    if not isinstance(profiles, dict) or not profiles:
        return default_config()
    for name, prof in list(profiles.items()):
        if not isinstance(prof, dict):
            profiles[name] = {p: NONE_NAME for p in PADDLES}
            continue
        for p in PADDLES:
            if prof.get(p) not in TARGETS:
                prof[p] = NONE_NAME
    cfg["profiles"] = profiles
    if cfg.get("active") not in profiles:
        cfg["active"] = next(iter(profiles))
    return cfg


def save_config(cfg, path=CONFIG_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2))
    os.replace(tmp, path)  # the service sees one complete file, never half of one


def rules_text(config_path):
    """The rules file the kernel loader reads: one line per paddle that does something."""
    cfg = load_config(config_path)
    prof = cfg["profiles"][cfg["active"]]
    lines = []
    for i, p in enumerate(PADDLES):
        t = TARGETS.get(prof.get(p))
        if t:
            lines.append(f"{i} {t[0]} {t[1]} {t[2]} {t[3]}")
    return "\n".join(lines) + "\n"

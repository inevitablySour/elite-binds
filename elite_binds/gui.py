#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Window for choosing what the Elite's back paddles do. Changes are saved at once and picked up by the running service."""
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eb_common as eb  # noqa: E402

TARGET_NAMES = list(eb.TARGETS)
SERVICE = "elite-binds-bpf.service"


def systemctl(*args):
    return subprocess.run(["systemctl", *args], capture_output=True, text=True, timeout=3)


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Elite Binds")
        self.set_default_size(460, -1)
        self.cfg = eb.load_config()
        self.loading = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(16)
        self.set_child(box)

        intro = Gtk.Label(label="Choose what each back paddle does. Changes apply straight away.")
        intro.set_wrap(True)
        intro.set_xalign(0)
        box.append(intro)

        # profile row
        prof_row = Gtk.Box(spacing=8)
        prof_row.append(Gtk.Label(label="Profile"))
        self.profile_model = Gtk.StringList()
        self.profile_drop = Gtk.DropDown(model=self.profile_model)
        self.profile_drop.set_hexpand(True)
        self.profile_drop.connect("notify::selected", self.on_profile_changed)
        prof_row.append(self.profile_drop)
        new_btn = Gtk.Button(label="New…")
        new_btn.connect("clicked", self.on_new_profile)
        prof_row.append(new_btn)
        self.del_btn = Gtk.Button(label="Delete")
        self.del_btn.connect("clicked", self.on_delete_profile)
        prof_row.append(self.del_btn)
        box.append(prof_row)

        # one row per paddle
        grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.drops = {}
        for i, p in enumerate(eb.PADDLES):
            label = Gtk.Label(label=eb.PADDLE_LABELS[p])
            label.set_xalign(0)
            drop = Gtk.DropDown(model=Gtk.StringList.new(TARGET_NAMES))
            drop.set_hexpand(True)
            drop.connect("notify::selected", self.on_paddle_changed, p)
            grid.attach(label, 0, i, 1, 1)
            grid.attach(drop, 1, i, 1, 1)
            self.drops[p] = drop
        box.append(grid)

        # status row
        self.status = Gtk.Label(xalign=0)
        self.status.set_wrap(True)
        box.append(self.status)
        svc_row = Gtk.Box(spacing=8)
        self.start_btn = Gtk.Button(label="Start")
        self.start_btn.connect("clicked", lambda *_: self.service("start"))
        self.stop_btn = Gtk.Button(label="Stop")
        self.stop_btn.connect("clicked", lambda *_: self.service("stop"))
        svc_row.append(self.start_btn)
        svc_row.append(self.stop_btn)
        box.append(svc_row)
        note = Gtk.Label(label="Paddle remapping runs inside the kernel as a background service, so games see your normal controller. No restart is needed after changing a paddle.")
        note.set_wrap(True)
        note.set_xalign(0)
        note.add_css_class("dim-label")
        box.append(note)

        self.fill_profiles()
        self.refresh_status()
        GLib.timeout_add_seconds(2, self.refresh_status)

    # -- profiles
    def fill_profiles(self):
        self.loading = True
        names = list(self.cfg["profiles"])
        self.profile_model.splice(0, self.profile_model.get_n_items(), names)
        self.profile_drop.set_selected(names.index(self.cfg["active"]))
        self.loading = False
        self.show_profile()

    def show_profile(self):
        self.loading = True
        prof = self.cfg["profiles"][self.cfg["active"]]
        for p in eb.PADDLES:
            self.drops[p].set_selected(TARGET_NAMES.index(prof[p]))
        self.del_btn.set_sensitive(len(self.cfg["profiles"]) > 1)
        self.loading = False

    def on_profile_changed(self, drop, _):
        if self.loading:
            return
        names = list(self.cfg["profiles"])
        self.cfg["active"] = names[drop.get_selected()]
        eb.save_config(self.cfg)
        self.show_profile()

    def on_paddle_changed(self, drop, _, paddle):
        if self.loading:
            return
        self.cfg["profiles"][self.cfg["active"]][paddle] = TARGET_NAMES[drop.get_selected()]
        eb.save_config(self.cfg)

    def on_new_profile(self, _btn):
        dialog = Gtk.Window(title="New profile", transient_for=self, modal=True)
        dialog.set_default_size(320, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(14)
        entry = Gtk.Entry(placeholder_text="Name, for example Longshot")
        box.append(entry)
        ok = Gtk.Button(label="Create (copies the current profile)")

        def create(*_):
            name = entry.get_text().strip()
            if not name or name in self.cfg["profiles"]:
                return
            self.cfg["profiles"][name] = dict(self.cfg["profiles"][self.cfg["active"]])
            self.cfg["active"] = name
            eb.save_config(self.cfg)
            self.fill_profiles()
            dialog.close()

        ok.connect("clicked", create)
        entry.connect("activate", create)
        box.append(ok)
        dialog.set_child(box)
        dialog.present()

    def on_delete_profile(self, _btn):
        if len(self.cfg["profiles"]) < 2:
            return
        del self.cfg["profiles"][self.cfg["active"]]
        self.cfg["active"] = next(iter(self.cfg["profiles"]))
        eb.save_config(self.cfg)
        self.fill_profiles()

    # -- service
    def service(self, what):
        # pkexec shows the system's password prompt; run it in the background so the window never freezes
        self.status.set_text("Waiting for your password ..." )
        try:
            proc = subprocess.Popen(["pkexec", "systemctl", what, SERVICE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            self.status.set_text("pkexec is not available.")
            return

        def done():
            if proc.poll() is None:
                return True
            self.refresh_status()
            return False
        GLib.timeout_add(500, done)

    def refresh_status(self):
        try:
            state = systemctl("is-active", SERVICE).stdout.strip()
        except subprocess.TimeoutExpired:
            state = "unknown"
        try:
            detail = Path("/run/elite-binds/status").read_text().strip()
        except OSError:
            detail = ""
        self.start_btn.set_sensitive(state != "active")
        self.stop_btn.set_sensitive(state == "active")
        if state == "active":
            self.status.set_text("Service running: " + (detail or "starting"))
        elif state in ("inactive", "failed"):
            self.status.set_text("Service not running. Start it with: sudo systemctl start elite-binds-bpf")
        else:
            self.status.set_text("Service not installed yet. Run: sudo ~/Development/elite-binds/bpf/install.sh")
        return True


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.elitebinds.App")

    def do_activate(self):
        win = self.props.active_window or Window(self)
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv[:1]))

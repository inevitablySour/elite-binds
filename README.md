# Elite Binds

Remap the four back paddles of an Xbox Elite Series 2 controller on Linux, over Bluetooth, without a virtual
controller. A small program running inside the kernel (HID-BPF) rewrites each paddle press into the button you
choose before the driver reads it. Games talk to your real controller, so rumble, the Xbox button and everything
else behave exactly as they do without this tool.

On Windows the Xbox Accessories app does this by writing profiles into the controller. Nothing public can do that
on Linux, so this tool does the translation in software instead. Nothing is written to the controller.

## How it behaves

- The paddles P1 to P4 (top left, bottom left, top right, bottom right) can each act as any of: A, B, X, Y,
  LB, RB, LT, RT, the stick clicks, View, Menu, Xbox, or a D-pad direction.
- Changes apply within about a second, with no restart.
- The remapping lives in a system service that starts at boot and re-attaches when the controller reconnects.
  The settings window is only a front end for the settings file.
- Profiles can be created in the window; the active one is used.

## Requirements

- A Linux kernel with HID-BPF (`CONFIG_HID_BPF=y`, `CONFIG_DEBUG_INFO_BTF=y`). Kernel 6.18 was used here.
- The [xpadneo](https://github.com/atar-axis/xpadneo) driver. The button positions in this tool follow what
  xpadneo expects. Another driver would need different positions.
- Build tools: `clang`, `bpftool`, `libbpf-dev`, `libelf-dev`, `zlib1g-dev`, `gcc`, `make`.
  On Debian and Ubuntu: `sudo apt install clang libbpf-dev bpftool libelf-dev zlib1g-dev build-essential`.
- For the settings window: Python 3 with GTK 4 (`python3-gi`, `gir1.2-gtk-4.0`) and `pkexec` (polkit).

## Install

```
make
sudo ./install.sh
```

Then open "Elite Binds" from your applications menu, or run `elite-binds-gui`. The window has Start and Stop
buttons for the service; they ask for your password. To remove everything: `sudo ./uninstall.sh`.

Your settings are kept in `~/.config/elite-binds/config.json`. You can edit that file by hand; the service re-reads
it when it changes.

## Limits

- Bluetooth only. A USB connection uses a different report format that this does not handle.
- Tested on one Xbox Elite Series 2 (Bluetooth, product ID 045E:0B22) with xpadneo `v0.11-pre-99`
  on Pop!_OS 24.04 and kernel 6.18. Other firmware versions may differ.
- The paddles must be in the controller's default state (no hardware profile light lit). In a hardware profile the
  controller sends its own button codes instead of the paddle bits.
- Programs that read the controller's raw HID data (some launchers do) also see the rewritten report, which is
  normally what you want.
- Triggers are set to fully pressed; there is no partial press.
- The D-pad targets only apply while the real D-pad is untouched.
- The service runs as root, because loading a kernel program needs it. Read `elite_binds/service.py` and
  `bpf/eb.bpf.c` before installing; both are short.

## Other files

- `docs/how-it-works.md`: the report layout, why the button positions are what they are, and how to adapt this.
- `tools/hid-capture.py` and `tools/paddle-bits.py`: print which bytes and bits change when you press buttons.
  Use them to check a different controller or firmware.
- `tools/test.sh`: loads a temporary test mapping (P1=A, P2=B, P3=X, P4=Y) without the service.

## License

GPL-2.0-only. The kernel program must be GPL to load. See `LICENSE`.

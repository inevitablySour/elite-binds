# How it works

## The idea

The kernel lets a small verified program hook a HID device and edit each input report before the driver parses it
(HID-BPF, `struct hid_bpf_ops` with a `hid_device_event` hook). `bpf/eb.bpf.c` does one thing: for each of the four
paddle bits, if the bit is set, clear it and set the bit of the target button instead.

`bpf/eb-loader.c` attaches that program to one HID device. HID-BPF programs attach to a specific HID id (the number
after the dot in `/sys/bus/hid/devices/0005:045E:0B22.00B1`, here `0xB1`). That id changes every time the controller
reconnects, so `elite_binds/service.py` watches for the device and runs the loader again with the new id. It also
rewrites the loader's rules file when the settings change and sends the loader a SIGHUP.

## The input report

Report id 1 over Bluetooth is 20 bytes. These positions are in the controller's original layout, which is what the
kernel program sees:

| Bytes | Content |
|---|---|
| 1 to 8 | left and right stick, 16 bits each |
| 9 to 10 | left trigger, 10 bits |
| 11 to 12 | right trigger, 10 bits |
| 13 | D-pad, low nibble: 1 up, 3 right, 5 down, 7 left, 0 neutral |
| 14 | bit 0 A, bit 1 B, bit 3 X, bit 4 Y, bit 6 LB, bit 7 RB |
| 15 | bit 3 Menu, bit 4 Xbox, bit 5 left stick click, bit 6 right stick click |
| 16 | bit 0 View |
| 19 | bits 0 to 3: the four paddles |

Byte 18 changes on its own (status) and is ignored.

## A trap worth knowing

xpadneo rearranges this report in place right after the kernel program runs (see `xpadneo_events_raw_event` in its
`events.c`): X and Y move down one bit, LB and RB two, and View, Menu, the stick clicks and the Xbox button move
to other bytes. A tool that reads the report through `hidraw` sees the rearranged version. The first version of this
project used those positions and only A and B (which do not move) worked. Always write the original positions, as in
the table above.

## Why not a virtual controller

The first version grabbed the real controller and presented a virtual one, forwarding rumble. It worked for buttons,
but forwarding rumble between two devices froze a process inside the kernel (an uninterruptible wait in
`evdev_release`), leaving a stuck button until reboot. Rewriting the report in the kernel avoids a second device
and keeps rumble untouched.

## Adapting it

To check another controller or firmware, run `tools/hid-capture.py` with `sudo` and press each button, then
`tools/paddle-bits.py` for the paddles. The tools read the report after the driver has rearranged it, so compare with
the driver source before writing positions into `elite_binds/eb_common.py`.

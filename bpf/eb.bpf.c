// SPDX-License-Identifier: GPL-2.0-only
// Rewrites the Elite 2's raw Bluetooth input report before the driver reads it:
// a paddle press is cleared and shows up as another button instead. Report layout verified by capture.
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

#define REPORT_LEN 20
#define PADDLE_BYTE 19

enum { R_NONE = 0, R_BUTTON = 1, R_HAT = 2, R_TRIGGER = 3 };

struct rule {
	__u8 type; /* R_* */
	__u8 off;  /* R_BUTTON: byte of the button bit; R_TRIGGER: first byte of the 16-bit trigger value */
	__u8 mask; /* R_BUTTON: bit to set */
	__u8 val;  /* R_HAT: hat value 1..8 */
};

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 4);
	__type(key, __u32);
	__type(value, struct rule);
} rules SEC(".maps");

extern __u8 *hid_bpf_get_data(struct hid_bpf_ctx *ctx, unsigned int offset, const size_t __sz) __ksym;

static __always_inline void apply(__u8 *d, __u32 i, __u8 bit)
{
	struct rule *r = bpf_map_lookup_elem(&rules, &i);

	if (!r || r->type == R_NONE || !(d[PADDLE_BYTE] & bit))
		return;
	d[PADDLE_BYTE] &= ~bit;
	if (r->type == R_BUTTON) {
		/* fixed offsets only: the kernel's checker rejects a computed index into the report */
		if (r->off == 14)
			d[14] |= r->mask;
		else if (r->off == 15)
			d[15] |= r->mask;
		else if (r->off == 16)
			d[16] |= r->mask;
	} else if (r->type == R_HAT) {
		if ((d[13] & 0x0f) == 0)
			d[13] = (d[13] & 0xf0) | (r->val & 0x0f);
	} else if (r->type == R_TRIGGER) {
		if (r->off == 9) {
			d[9] = 0xff;
			d[10] = (d[10] & 0xfc) | 0x03;
		} else if (r->off == 11) {
			d[11] = 0xff;
			d[12] = (d[12] & 0xfc) | 0x03;
		}
	}
}

SEC("struct_ops/hid_device_event")
int BPF_PROG(eb_event, struct hid_bpf_ctx *hctx, enum hid_report_type type, __u64 source)
{
	__u8 *d = hid_bpf_get_data(hctx, 0, REPORT_LEN);

	if (!d || d[0] != 1)
		return 0;
	apply(d, 0, 0x01);
	apply(d, 1, 0x02);
	apply(d, 2, 0x04);
	apply(d, 3, 0x08);
	return 0;
}

SEC(".struct_ops.link")
struct hid_bpf_ops eb_ops = {
	.hid_device_event = (void *)eb_event,
};

char _license[] SEC("license") = "GPL";

// SPDX-License-Identifier: GPL-2.0-only
// Loads the paddle-remap program onto one HID device and keeps it there.
// usage: eb-loader <hid-id> <rules-file>     (SIGHUP re-reads the rules, SIGTERM/SIGINT removes the program)
// rules file: one line per paddle:  <index 0-3> <type> <off> <mask> <val>   (numbers, 0x.. allowed)
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <elf.h>

#ifndef EB_OBJ
#define EB_OBJ "eb.bpf.o"
#endif
struct rule { unsigned char type, off, mask, val; };
static volatile sig_atomic_t reload, quit;
static void on_hup(int s) { reload = 1; }
static void on_term(int s) { quit = 1; }


/* libbpf 1.3 gives no access to the struct_ops data, so write the hid id into the object file image
 * (first field of struct hid_bpf_ops, inside the ".struct_ops.link" section) before libbpf reads it. */
static char *read_patched(const char *path, int hid_id, size_t *len)
{
	FILE *f = fopen(path, "rb");
	char *buf;
	long n;
	Elf64_Ehdr *eh;
	Elf64_Shdr *sh;
	const char *names;

	if (!f) return NULL;
	fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
	buf = malloc(n);
	if (!buf || fread(buf, 1, n, f) != (size_t)n) { fclose(f); return NULL; }
	fclose(f);
	eh = (Elf64_Ehdr *)buf;
	sh = (Elf64_Shdr *)(buf + eh->e_shoff);
	names = buf + sh[eh->e_shstrndx].sh_offset;
	for (int i = 0; i < eh->e_shnum; i++) {
		if (!strcmp(names + sh[i].sh_name, ".struct_ops.link")) {
			memcpy(buf + sh[i].sh_offset, &hid_id, sizeof(hid_id));
			*len = n;
			return buf;
		}
	}
	return NULL;
}

static struct bpf_map *rules_map;

static int load_rules(const char *path)
{
	FILE *f = fopen(path, "r");
	struct rule none[4] = {0};
	int fd = bpf_map__fd(rules_map);
	unsigned idx, type, off, mask, val;

	if (!f) { perror(path); return -1; }
	for (unsigned k = 0; k < 4; k++) bpf_map_update_elem(fd, &k, &none[k], 0);
	while (fscanf(f, "%i %i %i %i %i", &idx, &type, &off, &mask, &val) == 5) {
		struct rule r = { type, off, mask, val };
		if (idx < 4) bpf_map_update_elem(fd, &idx, &r, 0);
	}
	fclose(f);
	return 0;
}

int main(int argc, char **argv)
{
	struct bpf_object *obj;
	struct bpf_map *ops;
	struct bpf_link *link;

	if (argc < 3 || argc > 4) { fprintf(stderr, "usage: %s <hid-id> <rules-file> [object-file]\n", argv[0]); return 2; }
	{
		size_t len;
		char *img = read_patched(argc == 4 ? argv[3] : EB_OBJ, atoi(argv[1]), &len);
		if (!img) { fprintf(stderr, "cannot read/patch " EB_OBJ "\n"); return 1; }
		obj = bpf_object__open_mem(img, len, NULL);
	}
	if (!obj) { fprintf(stderr, "cannot open the program image\n"); return 1; }
	ops = bpf_object__find_map_by_name(obj, "eb_ops");
	rules_map = bpf_object__find_map_by_name(obj, "rules");
	if (!ops || !rules_map) { fprintf(stderr, "maps missing\n"); return 1; }
	if (bpf_object__load(obj)) { fprintf(stderr, "load failed (needs root? verifier?)\n"); return 1; }
	if (load_rules(argv[2])) return 1;
	link = bpf_map__attach_struct_ops(ops);
	if (!link) { perror("attach"); return 1; }
	signal(SIGHUP, on_hup); signal(SIGTERM, on_term); signal(SIGINT, on_term);
	printf("attached to hid id %s\n", argv[1]); fflush(stdout);
	while (!quit) {
		if (reload) { reload = 0; load_rules(argv[2]); printf("rules reloaded\n"); fflush(stdout); }
		sleep(1);
	}
	bpf_link__destroy(link);
	bpf_object__close(obj);
	return 0;
}

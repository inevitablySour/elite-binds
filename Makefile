# Builds the kernel program and its loader into build/.
# Needs: clang, bpftool, libbpf-dev (and gcc, libelf-dev, zlib1g-dev).
BUILD := build
ARCH := $(shell uname -m | sed 's/x86_64/x86/; s/aarch64/arm64/')

all: $(BUILD)/eb-loader

$(BUILD)/vmlinux.h:
	mkdir -p $(BUILD)
	bpftool btf dump file /sys/kernel/btf/vmlinux format c > $@

$(BUILD)/eb.bpf.o: bpf/eb.bpf.c $(BUILD)/vmlinux.h
	clang -g -O2 -target bpf -D__TARGET_ARCH_$(ARCH) -I$(BUILD) -c $< -o $@

$(BUILD)/eb-loader: bpf/eb-loader.c $(BUILD)/eb.bpf.o
	gcc -O2 -Wall -DEB_OBJ='"$(CURDIR)/$(BUILD)/eb.bpf.o"' -o $@ $< -lbpf -lelf -lz

clean:
	rm -rf $(BUILD)

.PHONY: all clean

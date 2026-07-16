#!/bin/bash
set -euo pipefail

# Always run from the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEPLOY_DIR="${DEPLOY_DIR:-$SCRIPT_DIR/GCOV/build-vdevice_x86-64-mw/tmp/deploy/images/vdevice_x86-64-mw}"
DEFAULT_KERNEL_FILE="$DEPLOY_DIR/bzImage"
DEFAULT_ROOTFS_FILE="$DEPLOY_DIR/core-image-vdevice-xfce-vdevice_x86-64-mw-20260709120900.rootfs.ext4"
LEGACY_KERNEL_FILE="$SCRIPT_DIR/bzImage--5.15.184+git0+9c4fc176ec_9a9d15d3fc-r0-vdevice_x86-64-mw-20260701083926.bin"
LEGACY_ROOTFS_FILE="$SCRIPT_DIR/core-image-vdevice-xfce-vdevice_x86-64-mw-20260709120900.rootfs.ext4"

KERNEL_FILE="${KERNEL_FILE:-$DEFAULT_KERNEL_FILE}"
ROOTFS_FILE="${ROOTFS_FILE:-$DEFAULT_ROOTFS_FILE}"

if [[ ! -f "$KERNEL_FILE" && -f "$LEGACY_KERNEL_FILE" ]]; then
  KERNEL_FILE="$LEGACY_KERNEL_FILE"
fi

if [[ ! -f "$ROOTFS_FILE" && -f "$LEGACY_ROOTFS_FILE" ]]; then
  ROOTFS_FILE="$LEGACY_ROOTFS_FILE"
fi

# Sanity checks
[[ -f "$KERNEL_FILE" ]]  || { echo "Error: Kernel not found: $KERNEL_FILE" >&2; exit 1; }
[[ -f "$ROOTFS_FILE" ]]  || { echo "Error: Rootfs not found: $ROOTFS_FILE" >&2; exit 1; }

# QEMU binary (MINGW64)
QEMU_BIN="/mingw64/bin/qemu-system-x86_64"
[[ -x "$QEMU_BIN" ]] || { echo "Error: $QEMU_BIN not executable. Install 'mingw-w64-x86_64-qemu' in MSYS2 MINGW64." >&2; exit 1; }

# Recommended: bump to 1536–2048 MB if you run XFCE
RAM_MB="${RAM_MB:-1024}"

# Kernel command line:
#  - console=ttyS0            → get full logs in the serial window
#  - root=/dev/vda            → virtio-blk device name
#  - rw rootwait              → wait for block device; mount read-write
#  - init=/sbin/init          → systemd via /sbin/init symlink
APPEND="video=1280x720 console=ttyS0 root=/dev/vda rw rootwait init=/sbin/init"

"$QEMU_BIN" \
  -accel whpx \
  -cpu IvyBridge \
  -machine q35 \
  -kernel "$KERNEL_FILE" \
  -append "$APPEND" \
  -drive file="$ROOTFS_FILE",if=virtio,format=raw \
  -serial mon:stdio \
  -smp 8 \
  -m "$RAM_MB" \
  -display sdl,gl=on \
  -vga none \
  -device virtio-gpu-gl,max_outputs=1 \
  -device usb-tablet \
  -netdev user,id=network0 \
  -device virtio-net,netdev=network0 \
  -usb \
  -device usb-host,vendorid=0x0bb4,productid=0x0a5f \
  -audiodev id=snd0,driver=sdl \
  -device ich9-intel-hda \
  -device hda-duplex,audiodev=snd0 \
  -nic user,ipv6=off,model=e1000,id=network_0,net=10.0.8.0/24,hostfwd=tcp:127.0.0.1:5522-:22
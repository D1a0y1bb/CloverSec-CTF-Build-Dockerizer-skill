#!/bin/bash
set -euo pipefail

cd /opt/copyfail

if [[ -n "${FLAG:-${CTF_FLAG:-}}" ]]; then
  /changeflag.sh "${FLAG:-${CTF_FLAG:-}}"
fi

QEMU_MEMORY="${QEMU_MEMORY:-768M}"
QEMU_CPUS="${QEMU_CPUS:-2}"
KERNEL="/opt/copyfail/vm/vmlinuz"
INITRD="/opt/copyfail/vm/initrd.img"
ROOTFS="/opt/copyfail/vm/rootfs.ext4"

echo "[INFO] Copy Fail QEMU 靶机正在启动"
echo "[INFO] SSH 用户: ctf / 123456"
echo "[INFO] 验证脚本需从题目附件上传到 /tmp 后执行"
echo "[INFO] 内核: $(cat /opt/copyfail/vm/kernel-version 2>/dev/null || echo unknown)"

exec qemu-system-x86_64 \
  -machine q35,accel=tcg \
  -cpu max \
  -m "${QEMU_MEMORY}" \
  -smp "${QEMU_CPUS}" \
  -kernel "${KERNEL}" \
  -initrd "${INITRD}" \
  -append "root=/dev/vda rw console=ttyS0 net.ifnames=0 biosdevname=0 panic=1 init=/sbin/copyfail-init" \
  -drive "file=${ROOTFS},format=raw,if=virtio,cache=writeback" \
  -netdev user,id=net0,hostfwd=tcp::22-:22 \
  -device e1000,netdev=net0 \
  -nographic \
  -no-reboot

#!/bin/bash
set -euo pipefail


# Linux-QEMU 栈启动脚本：平台执行 /start.sh，漏洞内核在 QEMU guest 中运行。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
:


cd "/opt/linux-qemu"
: # defense block disabled

if [[ -n "${FLAG:-${CTF_FLAG:-}}" ]]; then
  /changeflag.sh
fi

QEMU_BINARY="qemu-system-x86_64"
VM_KERNEL="vm/vmlinuz"
VM_INITRD=""
VM_ROOTFS="vm/rootfs.ext4"
VM_ACCELERATOR="tcg"
VM_REQUIRE_KVM="false"
KERNEL_APPEND='console=ttyS0 root=/dev/vda rw init=/sbin/init panic=-1'
QEMU_EXTRA_ARGS=""

REQUIRED_VM_ASSETS=("${VM_KERNEL}" "${VM_ROOTFS}")
if [[ -n "${VM_INITRD}" ]]; then
  REQUIRED_VM_ASSETS+=("${VM_INITRD}")
fi

for required in "${QEMU_BINARY}" "${REQUIRED_VM_ASSETS[@]}"; do
  if [[ "${required}" == "${QEMU_BINARY}" ]]; then
    command -v "${required}" >/dev/null 2>&1 || {
      echo "[ERROR] QEMU binary 不存在: ${required}" >&2
      exit 2
    }
  elif [[ ! -f "${required}" ]]; then
    echo "[ERROR] VM asset 不存在: ${required}" >&2
    exit 2
  fi
done

case "${VM_ACCELERATOR}" in
  auto)
    if [[ -e /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
      VM_ACCELERATOR="kvm"
    else
      VM_ACCELERATOR="tcg"
    fi
    ;;
  kvm)
    if [[ ! -e /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
      echo "[ERROR] challenge.vm.accelerator=kvm 但 /dev/kvm 不可用" >&2
      exit 2
    fi
    ;;
  tcg)
    ;;
  *)
    echo "[ERROR] unsupported VM_ACCELERATOR=${VM_ACCELERATOR}" >&2
    exit 2
    ;;
esac

if [[ "${VM_REQUIRE_KVM}" == "true" && "${VM_ACCELERATOR}" != "kvm" ]]; then
  echo "[ERROR] challenge.vm.require_kvm=true 但未使用 KVM" >&2
  exit 2
fi

echo "[INFO] linux-qemu accelerator=${VM_ACCELERATOR} forwards=tcp:22->22"
echo "[INFO] kernel=${VM_KERNEL} initrd=${VM_INITRD} rootfs=${VM_ROOTFS}"

QEMU_ARGS=(
  -machine "q35,accel=${VM_ACCELERATOR}"
  -cpu "max"
  -m "768M"
  -smp "2"
  -kernel "${VM_KERNEL}"
)

if [[ -n "${VM_INITRD}" ]]; then
  QEMU_ARGS+=(-initrd "${VM_INITRD}")
fi

QEMU_ARGS+=(
  -append "${KERNEL_APPEND}"
  -drive "file=${VM_ROOTFS},format=raw,if=virtio"
  -netdev "user,id=net0,hostfwd=tcp::22-:22"
  -device "e1000,netdev=net0"
  -nographic
  -monitor "none"
  -no-reboot
)

if [[ -n "${QEMU_EXTRA_ARGS}" ]]; then
  read -r -a EXTRA_ARGS_ARRAY <<< "${QEMU_EXTRA_ARGS}"
  QEMU_ARGS+=("${EXTRA_ARGS_ARRAY[@]}")
fi

exec "${QEMU_BINARY}" "${QEMU_ARGS[@]}"

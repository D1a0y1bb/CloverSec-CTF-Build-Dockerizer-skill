{{> snippets/start-header.tpl }}

# Linux-QEMU 栈启动脚本：平台执行 /start.sh，漏洞内核在 QEMU guest 中运行。
{{RDG_FLAG_START_BLOCK}}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"
{{DEFENSE_START_BLOCK}}

if [[ -n "${FLAG:-${CTF_FLAG:-}}" ]]; then
  /changeflag.sh
fi

QEMU_BINARY="{{VM_QEMU_BINARY}}"
VM_KERNEL="{{VM_KERNEL}}"
VM_INITRD="{{VM_INITRD}}"
VM_ROOTFS="{{VM_ROOTFS}}"
VM_ACCELERATOR="{{VM_ACCELERATOR}}"
VM_REQUIRE_KVM="{{VM_REQUIRE_KVM}}"
KERNEL_APPEND={{VM_APPEND_QUOTED}}
QEMU_EXTRA_ARGS="{{VM_EXTRA_ARGS}}"

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

echo "[INFO] linux-qemu accelerator=${VM_ACCELERATOR} forwards={{VM_GUEST_FORWARDS}}"
echo "[INFO] kernel=${VM_KERNEL} initrd=${VM_INITRD} rootfs=${VM_ROOTFS}"

QEMU_ARGS=(
  -machine "{{VM_MACHINE}},accel=${VM_ACCELERATOR}"
  -cpu "{{VM_CPU}}"
  -m "{{VM_MEMORY}}"
  -smp "{{VM_CPUS}}"
  -kernel "${VM_KERNEL}"
)

if [[ -n "${VM_INITRD}" ]]; then
  QEMU_ARGS+=(-initrd "${VM_INITRD}")
fi

QEMU_ARGS+=(
  -append "${KERNEL_APPEND}"
  -drive "file=${VM_ROOTFS},format={{VM_DRIVE_FORMAT}},if=virtio"
  -netdev "{{VM_NETDEV}}"
  -device "{{VM_NET_DEVICE}},netdev={{VM_NETDEV_ID}}"
  -nographic
  -monitor "{{VM_MONITOR}}"
  -no-reboot
)

if [[ -n "${QEMU_EXTRA_ARGS}" ]]; then
  read -r -a EXTRA_ARGS_ARRAY <<< "${QEMU_EXTRA_ARGS}"
  QEMU_ARGS+=("${EXTRA_ARGS_ARRAY[@]}")
fi

exec "${QEMU_BINARY}" "${QEMU_ARGS[@]}"

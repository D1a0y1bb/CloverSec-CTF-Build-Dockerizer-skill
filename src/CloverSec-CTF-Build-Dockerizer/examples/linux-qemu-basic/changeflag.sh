#!/bin/bash
set -euo pipefail

# linux-qemu 动态 flag 写入入口：保留外层 /flag，并按配置写入 guest rootfs。
TARGET_PATH="${FLAG_PATH:-/flag}"
DEFAULT_FLAG="flag{dynamic_flag_placeholder}"
if [[ -n "${FLAG:-}" ]]; then
  TARGET_FLAG="${FLAG}"
elif [[ -n "${CTF_FLAG:-}" ]]; then
  TARGET_FLAG="${CTF_FLAG}"
elif [[ $# -gt 0 && -n "${1:-}" ]]; then
  TARGET_FLAG="$1"
else
  TARGET_FLAG="${DEFAULT_FLAG}"
fi
VM_ROOTFS="${VM_ROOTFS:-vm/rootfs.ext4}"
GUEST_FLAG_PATH="${GUEST_FLAG_PATH:-/root/flag}"
FLAG_INJECTION="${FLAG_INJECTION:-debugfs}"

if [[ -z "${TARGET_PATH}" ]]; then
  echo "[ERROR] FLAG_PATH 不能为空" >&2
  exit 2
fi

mkdir -p "$(dirname "${TARGET_PATH}")"
printf '%s\n' "${TARGET_FLAG}" > "${TARGET_PATH}"
chmod 444 "${TARGET_PATH}" || true


if [[ "${FLAG_INJECTION}" == "none" ]]; then
  echo "[INFO] flag updated at ${TARGET_PATH}; guest flag injection disabled"
  exit 0
fi

if [[ "${FLAG_INJECTION}" != "debugfs" ]]; then
  echo "[ERROR] unsupported FLAG_INJECTION=${FLAG_INJECTION}" >&2
  exit 2
fi

if ! command -v debugfs >/dev/null 2>&1; then
  echo "[ERROR] debugfs 不存在，无法写入 guest rootfs" >&2
  exit 2
fi
if [[ ! -f "${VM_ROOTFS}" ]]; then
  echo "[ERROR] VM rootfs 不存在: ${VM_ROOTFS}" >&2
  exit 2
fi

tmp_flag="$(mktemp)"
printf '%s\n' "${TARGET_FLAG}" > "${tmp_flag}"
debugfs -w -R "rm ${GUEST_FLAG_PATH}" "${VM_ROOTFS}" >/dev/null 2>&1 || true
debugfs -w -R "write ${tmp_flag} ${GUEST_FLAG_PATH}" "${VM_ROOTFS}" >/dev/null
debugfs -w -R "set_inode_field ${GUEST_FLAG_PATH} mode 0100400" "${VM_ROOTFS}" >/dev/null || true
debugfs -w -R "set_inode_field ${GUEST_FLAG_PATH} uid 0" "${VM_ROOTFS}" >/dev/null || true
debugfs -w -R "set_inode_field ${GUEST_FLAG_PATH} gid 0" "${VM_ROOTFS}" >/dev/null || true
rm -f "${tmp_flag}"
echo "[INFO] flag updated at ${TARGET_PATH} and guest:${GUEST_FLAG_PATH}"

#!/bin/bash
set -euo pipefail

TARGET_PATH="${FLAG_PATH:-/flag}"
DEFAULT_FLAG="flag{1c7e3f0d0bb24759931f6e80d877c431}"
if [[ -n "${FLAG:-}" ]]; then
  TARGET_FLAG="${FLAG}"
elif [[ -n "${CTF_FLAG:-}" ]]; then
  TARGET_FLAG="${CTF_FLAG}"
elif [[ $# -gt 0 && -n "${1:-}" ]]; then
  TARGET_FLAG="$1"
else
  TARGET_FLAG="${DEFAULT_FLAG}"
fi
ROOTFS_IMAGE="/opt/copyfail/vm/rootfs.ext4"
FLAG_INJECTION="${FLAG_INJECTION:-debugfs}"

mkdir -p "$(dirname "${TARGET_PATH}")"
printf '%s\n' "${TARGET_FLAG}" > "${TARGET_PATH}"
chmod 444 "${TARGET_PATH}"
chown root:root "${TARGET_PATH}" 2>/dev/null || true

if [[ "${FLAG_INJECTION}" != "none" && -f "${ROOTFS_IMAGE}" ]]; then
  debugfs -w "${ROOTFS_IMAGE}" >/dev/null 2>&1 <<'EOF' || true
rm /root/flag
EOF
  debugfs -w "${ROOTFS_IMAGE}" >/dev/null <<EOF
write ${TARGET_PATH} /root/flag
sif /root/flag mode 0100400
sif /root/flag uid 0
sif /root/flag gid 0
EOF
fi

echo "[INFO] flag updated"

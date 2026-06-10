#!/bin/bash
set -euo pipefail

TARGET_FLAG="${1:-${FLAG:-${CTF_FLAG:-flag{1c7e3f0d0bb24759931f6e80d877c431}}}}"
ROOTFS_IMAGE="/opt/copyfail/vm/rootfs.ext4"

printf '%s\n' "${TARGET_FLAG}" > /flag
chmod 444 /flag
chown root:root /flag

if [[ -f "${ROOTFS_IMAGE}" ]]; then
  debugfs -w "${ROOTFS_IMAGE}" >/dev/null 2>&1 <<'EOF' || true
rm /root/flag
EOF
  debugfs -w "${ROOTFS_IMAGE}" >/dev/null <<EOF
write /flag /root/flag
sif /root/flag mode 0100400
sif /root/flag uid 0
sif /root/flag gid 0
EOF
fi

echo "[INFO] flag updated"

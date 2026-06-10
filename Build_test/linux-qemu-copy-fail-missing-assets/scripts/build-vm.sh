#!/bin/bash
set -euo pipefail

ROOT="/opt/copyfail/rootfs"
VM="/opt/copyfail/vm"
ROOTFS_MB="${ROOTFS_MB:-1200}"
SNAPSHOT_DATE="${SNAPSHOT_DATE:-20260320T000000Z}"
DEBIAN_SUITE="${DEBIAN_SUITE:-trixie}"
DEBIAN_MIRROR="${DEBIAN_MIRROR:-http://snapshot.debian.org/archive/debian/${SNAPSHOT_DATE}}"
DEBOOTSTRAP_CACHE="${DEBOOTSTRAP_CACHE:-/var/cache/copyfail-debootstrap}"
INCLUDE_PACKAGES="dropbear-bin,initramfs-tools,iproute2,kmod,linux-image-amd64,login,openssh-client,passwd,python3,util-linux"

rm -rf "${ROOT}" "${VM}"
mkdir -p "${ROOT}" "${VM}" "${DEBOOTSTRAP_CACHE}"

debootstrap \
  --no-check-gpg \
  --variant=minbase \
  --arch=amd64 \
  --cache-dir="${DEBOOTSTRAP_CACHE}" \
  --include="${INCLUDE_PACKAGES}" \
  "${DEBIAN_SUITE}" "${ROOT}" "${DEBIAN_MIRROR}"

cat > "${ROOT}/etc/apt/apt.conf.d/99copyfail-snapshot" <<'EOF'
Acquire::Check-Valid-Until "false";
Acquire::Retries "5";
Acquire::http::Timeout "30";
Acquire::https::Timeout "30";
APT::Get::Assume-Yes "true";
EOF

cat > "${ROOT}/etc/apt/sources.list" <<EOF
deb [check-valid-until=no] ${DEBIAN_MIRROR} ${DEBIAN_SUITE} main
EOF

cat > "${ROOT}/etc/hostname" <<'EOF'
copyfail-lab
EOF

cat > "${ROOT}/etc/hosts" <<'EOF'
127.0.0.1 localhost
127.0.1.1 copyfail-lab
EOF

mkdir -p "${ROOT}/etc/modules-load.d"
cat > "${ROOT}/etc/modules-load.d/copyfail.conf" <<'EOF'
algif_aead
authencesn
authenc
cbc
hmac
sha256_generic
EOF

chroot "${ROOT}" useradd -m -s /bin/bash ctf
printf 'ctf:123456\n' | chroot "${ROOT}" chpasswd
chroot "${ROOT}" passwd -l root

mkdir -p "${ROOT}/etc/dropbear"
chroot "${ROOT}" dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key >/dev/null

cat > "${ROOT}/sbin/copyfail-init" <<'EOF'
#!/bin/sh
set -eu

PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

mount -t proc proc /proc 2>/dev/null || true
mount -t sysfs sysfs /sys 2>/dev/null || true
mount -t devtmpfs devtmpfs /dev 2>/dev/null || true
mkdir -p /dev/pts /run /tmp
mount -t devpts devpts /dev/pts 2>/dev/null || true
mount -t tmpfs tmpfs /run 2>/dev/null || true
chmod 1777 /tmp

modprobe algif_aead 2>/dev/null || true
modprobe authencesn 2>/dev/null || true
modprobe authenc 2>/dev/null || true
modprobe cbc 2>/dev/null || true
modprobe hmac 2>/dev/null || true
modprobe sha256_generic 2>/dev/null || true

ip link set lo up 2>/dev/null || true
NET_IFACE=""
for iface in eth0 ens3 enp0s3; do
  if ip link show "$iface" >/dev/null 2>&1; then
    NET_IFACE="$iface"
    break
  fi
done
if [ -n "$NET_IFACE" ]; then
  ip link set "$NET_IFACE" up 2>/dev/null || true
  ip addr add 10.0.2.15/24 dev "$NET_IFACE" 2>/dev/null || true
  ip route add default via 10.0.2.2 2>/dev/null || true
fi
printf 'nameserver 10.0.2.3\n' > /etc/resolv.conf

echo "Copy Fail lab ready. SSH user: ctf / 123456"
exec /usr/sbin/dropbear -E -F -w -j -k -p 0.0.0.0:22 -r /etc/dropbear/dropbear_ed25519_host_key
EOF
chmod 555 "${ROOT}/sbin/copyfail-init"

cat > "${ROOT}/home/ctf/README-lab.md" <<'EOF'
# Copy Fail 漏洞实验环境

1. 执行 `id`，确认当前用户为 `ctf`。
2. 将题目附件中的验证脚本上传到 `/tmp`。
3. 执行 `python3 /tmp/kernel_precheck.py`，检查内核触发条件。
4. 执行 `python3 /tmp/copy_fail_exp.py`，进行漏洞验证。
5. 利用成功后执行 `id` 和 `cat /root/flag`，确认已经获得 root 权限并读取 flag。
EOF
chown 1000:1000 "${ROOT}/home/ctf/README-lab.md"
chmod 444 "${ROOT}/home/ctf/README-lab.md"

install -m 400 -o 0 -g 0 /flag "${ROOT}/root/flag"

KERNEL_PATH="$(find "${ROOT}/boot" -maxdepth 1 -name 'vmlinuz-*' | sort -V | tail -n 1)"
KERNEL_VERSION="${KERNEL_PATH##*/vmlinuz-}"
INITRD_PATH="${ROOT}/boot/initrd.img-${KERNEL_VERSION}"

cp "${KERNEL_PATH}" "${VM}/vmlinuz"
cp "${INITRD_PATH}" "${VM}/initrd.img"
printf '%s\n' "${KERNEL_VERSION}" > "${VM}/kernel-version"

truncate -s "${ROOTFS_MB}M" "${VM}/rootfs.ext4"
mkfs.ext4 -F -d "${ROOT}" "${VM}/rootfs.ext4"
e2fsck -f -y "${VM}/rootfs.ext4"
resize2fs -M "${VM}/rootfs.ext4"

rm -rf "${ROOT}"
chown -R root:root "${VM}"
chmod 444 "${VM}/vmlinuz" "${VM}/initrd.img" "${VM}/kernel-version"
chmod 644 "${VM}/rootfs.ext4"

# linux-qemu 模板

`linux-qemu` 用于 Linux kernel CVE/LPE 题目。外层容器仍按平台契约交付 `/start.sh`、`/changeflag.sh`、`/flag`；真实漏洞内核、initrd/rootfs 在 QEMU guest 中运行。

默认行为：

- 基础镜像：`debian:bookworm-slim`
- 运行依赖：`qemu-system-x86`、`qemu-system-arm`、`qemu-utils`、`e2fsprogs`、`openssh-client`
- 默认端口：`22`
- 默认加速：`tcg`
- 默认 flag 注入：`debugfs` 写入 guest rootfs 的 `/root/flag`

常用 `challenge.vm` 字段：

```yaml
vm:
  arch: x86_64
  qemu_binary: qemu-system-x86_64
  accelerator: tcg
  require_kvm: false
  memory: 768M
  cpus: 2
  kernel: vm/vmlinuz
  initrd: vm/initrd.img
  rootfs: vm/rootfs.ext4
  append: console=ttyS0 root=/dev/vda rw init=/sbin/init panic=-1
  guest_forwards:
    - proto: tcp
      host_port: "22"
      guest_port: "22"
  flag_injection: debugfs
  guest_flag_path: /root/flag
```

`guest_forwards[*].proto` 当前版本仅支持 `tcp`（自 `v2.1.0` 起）；如果选择 `qemu-system-aarch64`，Dockerfile 需要包含 `qemu-system-arm` 包。

`accelerator: auto` 会在 `/dev/kvm` 可读写时使用 KVM，否则使用 TCG。正式交付前必须验证平台是否允许 `/dev/kvm`；模板不会自动要求 `--privileged`。

# linux-qemu-basic

这是 `linux-qemu` 栈的轻量渲染示例，用于验证 `challenge.vm`、模板变量、`changeflag.sh` 和静态校验链路。

本目录中的 `vm/` 文件是占位文件，不是可启动 VM。默认回归只应执行 render/validate；完整 QEMU boot 需要替换为真实 `vmlinuz`、`rootfs.ext4` 后单独验证。需要 initrd 的内核可把 `challenge.vm.initrd` 改回 `vm/initrd.img` 并提供对应文件。

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
```

正式题目建议至少验证：

- QEMU 启动后 guest 服务可达
- Docker `EXPOSE` 与 QEMU `hostfwd` 一致
- `/changeflag.sh` 写入后 guest 内 `guest_flag_path` 读取到新 flag
- KVM/TCG 策略与平台权限一致

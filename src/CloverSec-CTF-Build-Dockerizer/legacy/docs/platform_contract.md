# Platform Contract

普通题目使用 `direct-exec-v1`。详细规则见 `platform_contract_v3.md`。

旧题目和旧平台调用 `/changeflag.sh` 时使用 `legacy-helper-v2`。旧版完整规则保存在 `platform_contract_legacy_v2.md`。

Linux-QEMU 使用 `linux-qemu-v1`，并保留 guest rootfs 注入流程。

## 当前默认启动

```bash
docker run -d <image> /start.sh
docker exec <container> sh -c 'printf "%s\n" "$1" > "$2"' sh "$new_flag" "$flag_path"
```

`flag.path` 表示题目程序实际读取的路径。

`start.sh` 不得初始化或覆盖通用 Flag。

## 合同选择

```yaml
challenge:
  platform:
    contract: direct-exec-v1
  flag:
    mode: direct_exec
    path: /flag
```

只有以下情况生成 `changeflag.sh`：

- `flag.mode=helper_script`。
- `platform.contract=legacy-helper-v2`。
- `flag.mode=qemu_guest`。
- `platform.contract=linux-qemu-v1`。

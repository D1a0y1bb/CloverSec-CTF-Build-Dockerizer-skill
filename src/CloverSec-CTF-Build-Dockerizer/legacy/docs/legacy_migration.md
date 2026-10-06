# Legacy Migration

## 旧题目

旧平台调用 `/changeflag.sh` 的题目可以显式设置：

```yaml
challenge:
  platform:
    contract: legacy-helper-v2
  flag:
    mode: helper_script
    path: /flag
```

Linux-QEMU 使用：

```yaml
challenge:
  platform:
    contract: linux-qemu-v1
  flag:
    mode: qemu_guest
```

## 当前平台题目

当前平台题目使用：

```yaml
challenge:
  platform:
    contract: direct-exec-v1
  flag:
    mode: direct_exec
    path: /home/ctf/flag
```

不要为了通过旧校验器添加 `changeflag.sh`。

迁移工具会保留原始 Dockerfile 和 start.sh，并在 `dist/` 输出交付副本。

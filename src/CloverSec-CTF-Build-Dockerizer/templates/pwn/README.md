# Pwn(xinetd/tcpserver/socat) 模板说明

## 适用场景

- CTF Jeopardy 模式 Pwn 题目（支持 xinetd/tcpserver/socat 前台托管）。
- 需要统一满足平台 `/start.sh` 和 Pwn 服务前台运行约束的交付。

> 说明：本模板不覆盖 AWD/AWDP 攻防编排。

## 默认值

- 默认端口：`10000`
- 默认工作目录：`/home/ctf`
- 默认启动命令：`/usr/sbin/xinetd -dontfork`（可回退 `tcpserver` 或 `socat`）
- 默认基础镜像：`debian:bookworm-slim`

## 变量说明

| 变量 | 说明 | 常见值 |
|---|---|---|
| `BASE_IMAGE` | 基础镜像 | `debian:bookworm-slim` |
| `WORKDIR` | 工作目录 | `/home/ctf` |
| `APP_SRC` | 构建上下文源路径 | `.` |
| `APP_DST` | 容器目标路径 | `/home/ctf` |
| `EXPOSE_PORTS` | 暴露端口 | `10000` |
| `START_CMD` | 前台启动命令 | `/usr/sbin/xinetd -dontfork` |
| `RUNTIME_DEPS_INSTALL` | 额外运行依赖安装片段 | `apt-get install ...` |
| `ENV_BLOCK` | 环境变量片段 | `ENV KEY=value` / `export KEY=value` |

## 最小 challenge.yaml 示例

```yaml
challenge:
  name: pwn-basic
  stack: pwn
  base_image: debian:bookworm-slim
  workdir: /home/ctf
  app_src: .
  app_dst: /home/ctf
  expose_ports: ["10000"]
  start:
    mode: cmd
    cmd: /usr/sbin/xinetd -dontfork
```

## 常见坑

1. `ctf.xinetd` 中二进制路径与 `WORKDIR` 不一致，导致服务启动失败。
2. 二进制缺少执行权限，建议在题目目录预先 `chmod +x`。
3. 若题目读取 `/home/ctf/flag`，请在 `challenge.flag.path` 写明该路径；direct-exec 不需要在 `start.sh` 中复制 Flag。
4. 只有旧平台明确调用 `/changeflag.sh` 时，才选择 `legacy-helper-v2` 并保留同步逻辑。

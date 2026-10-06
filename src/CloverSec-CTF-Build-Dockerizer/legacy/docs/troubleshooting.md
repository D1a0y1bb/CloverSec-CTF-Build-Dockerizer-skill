# 故障排查手册（Troubleshooting）

本文档用于定位 render、validate、build、run 各阶段问题。

## 目录

- 1. 渲染阶段
- 2. 校验阶段
- 3. 构建阶段
- 4. 运行阶段
- 5. 一键排查命令

## 1. 渲染阶段

### 1.1 报错：缺少 PyYAML

现象：

- `render.py` 输出 “缺少依赖 PyYAML”

处理：

```bash
python3 -m pip install -r scripts/requirements.txt
```

### 1.2 报错：模板变量未替换

现象：

- 渲染时报 `模板渲染后仍存在未替换变量`

处理：

- 检查 `challenge.yaml` 字段是否齐全。
- 检查模板中变量名是否和 `render.py` 输出变量一致。
- 检查 include 文件是否存在拼写错误。

---

## 2. 校验阶段

完整校验规则、ERROR/WARN 语义和 check-service 门禁见 `docs/validation_guide.md`。

### 2.1 报错：/start.sh 未复制到根目录

处理：

- 在 Dockerfile 增加：`COPY start.sh /start.sh`

### 2.2 报错：/flag 权限不正确

处理：

- 在 Dockerfile 增加：`RUN chmod 444 /flag`

### 2.3 报错：bash 缺失

处理：

- Debian/Ubuntu：`apt-get install -y --no-install-recommends bash`
- Alpine：`apk add --no-cache bash`

### 2.4 报错：单服务未使用 exec

处理：

- 将启动命令改为 `exec <主命令>`。

### 2.5 WARN：检测到 tail -f /dev/null

处理：

- 若已有服务命令，建议改为前台 exec 或 tail 真实日志。
- 若没有服务命令，必须改为启动真实服务。

---

## 3. 构建阶段

### 3.1 报错：apt 安装后镜像体积偏大

处理：

- 确保安装后有：`rm -rf /var/lib/apt/lists/*`

### 3.2 报错：pip 安装导致镜像膨胀

处理：

- 使用：`pip install --no-cache-dir ...`

### 3.3 报错：npm 安装慢且不可复现

处理：

- 优先 `npm ci`
- 安装后 `npm cache clean --force`

### 3.4 老题目在高版本运行时启动失败

现象：

- PHP/Node/Java 题目在默认镜像下报语法或依赖兼容错误。

处理：

- 优先在 AI 五问的 Q1 里确认“技术栈 + 运行时档位”。
- 或手动覆盖：
  - `render.py --runtime-profile <profile_id>`
  - `challenge.base_image: <exact_image>`
- 说明：命中 legacy 档位时，`validate.sh` 会给出 WARN（不阻断），用于提醒该镜像仅建议题目兼容使用。

---

## 4. 运行阶段

### 4.1 容器启动后立即退出

排查顺序：

1. `docker logs <container>` 看 start.sh 输出。
2. 检查 `start.sh` 最后是否是 `exec` 主进程。
3. 检查主命令是否存在（文件路径、二进制名）。

### 4.2 端口不通

排查顺序：

1. 应用是否监听 `0.0.0.0`。
2. Dockerfile 是否 `EXPOSE` 对应端口。
3. `docker run -p host:container` 端口映射是否正确。

### 4.3 日志无输出

排查顺序：

1. 应用是否输出到 stdout/stderr。
2. 多服务场景是否把日志重定向到真实日志文件并被 tail。
3. 避免使用空转命令掩盖真实日志。

### 4.4 WORKDIR 不一致

现象：

- validate 报 start.sh 与 Dockerfile WORKDIR 不一致

处理：

- 在 start.sh 中显式：`cd "<WORKDIR>"`

### 4.5 linux-qemu 启动失败

现象：

- `validate.sh` 报 QEMU 资产缺失
- 容器日志显示 `QEMU binary 不存在`
- 使用 KVM 时提示 `/dev/kvm` 不可用

处理：

- `asset_mode=prebuilt` 时确认 `vm/vmlinuz`、`vm/initrd.img`、`vm/rootfs.ext4` 位于构建上下文内。
- `asset_mode=build-script` 时确认 `challenge.vm.build_script` 指向的题目内脚本存在，且能在镜像构建期生成 VM 资产。
- 默认使用 `accelerator=tcg`；只有平台明确提供 `/dev/kvm` 时才使用 `accelerator=kvm` 或 `require_kvm=true`。
- 确认 `challenge.expose_ports` 与 `challenge.vm.guest_forwards[*].host_port` 一致。
- 正式交付不要默认开启 TCP monitor、gdbstub 或 `-S` 暂停启动。

### 4.6 linux-qemu 动态 flag 只在容器内变化

现象：

- `/flag` 已更新，但 guest 内 `/root/flag` 仍是旧值。

处理：

- 使用 `flag_injection=debugfs` 并确认镜像安装 `e2fsprogs`。
- 确认 `challenge.vm.rootfs` 指向可写 ext4 rootfs。
- 确认 `challenge.vm.guest_flag_path` 是 guest 内绝对路径，例如 `/root/flag`。

---

## 5. 一键排查命令

```bash
# 单目录渲染+校验
cd examples/node-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
```

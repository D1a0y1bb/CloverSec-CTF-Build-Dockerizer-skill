# Scenario Schema (v2.0.0)

`scenario.yaml` 用于描述**本地多服务编排与验证**，适合 AWD / AWDP / Vulhub-like 迁移场景。

它的职责是：

- 把多个单题目目录或 baseunit 组件渲染到统一输出目录；
- 生成仅供本地联调使用的 `docker-compose.yml`；
- 保持平台最终交付仍然是**每个服务各自的 `Dockerfile + start.sh`**。

## 设计边界

- `scenario.yaml` 不是平台最终投产格式。
- `docker-compose.yml` 只是本地联调与样例验证输出。
- 每个 service 最终仍渲染到：`output/services/<service-name>/`。
- AWDP 服务必须满足固定补丁契约：
  - `patch/src/`
  - `patch/patch.sh`
  - `patch_bundle.tar.gz`

## 顶层结构

```yaml
scenario:
  name: scenario-awd-basic
  mode: awd
  services:
    - name: web1
      challenge_path: ../node-basic/challenge.yaml
      profile: awd
      challenge:
        name: scenario-awd-web1
        start:
          mode: cmd
          cmd: node server.js
    - name: redis1
      component: redis
      variant: 7.2-alpine
      profile: awd
      host_ports:
        - "6379"
```

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `scenario.name` | 否 | 场景名，默认 `scenario` |
| `scenario.mode` | 否 | 场景默认 profile。支持 `jeopardy` / `rdg` / `awd` / `awdp` / `secops` |
| `scenario.services` | 是 | 服务列表 |

## `scenario.services[]`

每个 service 必须指定唯一 `name`，并且只能使用以下两类来源之一：

1. **题目目录来源**
- `project_dir`: 指向一个 challenge 目录，默认读取其中的 `challenge.yaml`
- `challenge_path`: 直接指向某个 `challenge.yaml`
- `challenge`: 可选的内联覆盖对象，用于改 `name/profile/start/expose_ports/...`

2. **组件来源**
- `component`: 组件名，例如 `redis`
- `variant`: 组件版本变体，例如 `7.2-alpine`
- 由 `render_component.py` 渲染为标准服务目录

> `service.challenge` 仅用于**字段覆盖对象**。若你想直接引用某个 challenge 文件，请使用 `challenge_path`。

## Service 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 服务名，必须唯一，同时会成为 `output/services/<name>/` 目录名 |
| `profile` | 否 | 当前服务显式 profile；若未设置，则按 `challenge.profile -> scenario.mode -> jeopardy` 继承 |
| `project_dir` | 条件必填 | challenge 目录路径，和 `challenge_path` 二选一 |
| `challenge_path` | 条件必填 | 指向某个 challenge.yaml 的路径，和 `project_dir` 二选一 |
| `challenge` | 否 | challenge 覆盖对象，按浅层合并；嵌套字典按同层键合并 |
| `component` | 条件必填 | 组件名；与 `variant` 一起使用 |
| `variant` | 条件必填 | 组件变体名 |
| `host_ports` | 否 | 宿主机映射端口列表；默认与 `challenge.expose_ports` 一一同值映射 |

## Profile 继承与一致性

推荐优先使用 `scenario.mode` 统一一组服务的行为，例如：

- `mode: awd`：所有服务都应渲染为 `profile=awd`
- `mode: awdp`：所有服务都应渲染为 `profile=awdp`

当前 `validate_scenario.py` 会对以下情况报错：

- `scenario.mode=awd`，但某个服务最终 `profile=awdp`
- `scenario.mode=awdp`，但某个服务最终 `profile=awd`

也就是说，`awd/awdp` 场景下，服务 profile 必须与场景 mode 对齐，或者通过继承得到相同值。

## AWDP 补丁契约

当服务最终 `profile=awdp` 时，渲染结果目录必须存在：

```text
patch/
patch/src/
patch/patch.sh
patch_bundle.tar.gz
```

校验器会检查：

- `patch/src/` 是目录
- `patch/patch.sh` 是文件且可执行
- `patch_bundle.tar.gz` 存在且可读取
- 补丁包内包含 `patch/patch.sh`
- 补丁包内包含 `patch/src/` 或其子项

## 输出结构

```text
<output>/
  scenario.yaml
  docker-compose.yml
  services/
    <service-a>/
      challenge.yaml
      Dockerfile
      start.sh
      ...
    <service-b>/
      challenge.yaml
      Dockerfile
      start.sh
      ...
```

## 示例 1：现有题目 + 组件服务混合

```yaml
scenario:
  name: scenario-awd-basic
  mode: awd
  services:
    - name: web1
      challenge_path: ../node-basic/challenge.yaml
      profile: awd
      challenge:
        name: scenario-awd-web1
        start:
          mode: cmd
          cmd: node server.js
    - name: redis1
      component: redis
      variant: 7.2-alpine
      profile: awd
      host_ports:
        - "6379"
```

## 示例 2：AWDP 服务

```yaml
scenario:
  name: scenario-awdp-basic
  mode: awdp
  services:
    - name: web1
      project_dir: ../node-awdp-basic
```

渲染后，`services/web1/` 必须存在 AWDP patch 目录与 `patch_bundle.tar.gz`。

## 命令示例

渲染：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd-basic
```

校验：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd-basic \
  --config /tmp/scenario-awd-basic/scenario.yaml
```

如需额外调用 `validate.sh` 校验每个服务目录，可追加：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd-basic \
  --config /tmp/scenario-awd-basic/scenario.yaml \
  --validate-rendered
```

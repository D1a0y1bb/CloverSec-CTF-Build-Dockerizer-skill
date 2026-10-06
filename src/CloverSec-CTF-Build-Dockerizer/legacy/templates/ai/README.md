# AI 模板说明（CPU 推理默认）

## 适用场景

- CTF Jeopardy 模式 AI 题目。
- 以 Flask/FastAPI + gunicorn 提供 Web 服务。
- 默认不依赖 GPU，强调可复现与稳定构建。

> 说明：本模板不覆盖 AWD/AWDP 攻防编排。

## 默认值

- 默认端口：`5000`
- 默认工作目录：`/app`
- 默认启动命令：`gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app`
- 默认基础镜像：`python:3.11-slim`

## 变量说明

| 变量 | 说明 | 常见值 |
|---|---|---|
| `BASE_IMAGE` | 基础镜像 | `python:3.11-slim` |
| `WORKDIR` | 工作目录 | `/app` |
| `APP_SRC` | 构建上下文源路径 | `.` |
| `APP_DST` | 容器目标路径 | `/app` |
| `EXPOSE_PORTS` | 暴露端口 | `5000` |
| `START_CMD` | 前台启动命令 | `gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app` |
| `PIP_REQUIREMENTS_BLOCK` | Python 安装片段（需 no-cache） | `pip install --no-cache-dir ...` |
| `ENV_BLOCK` | 环境变量片段 | `ENV KEY=value` / `export KEY=value` |

## 最小 challenge.yaml 示例

```yaml
challenge:
  name: ai-basic
  stack: ai
  base_image: python:3.11-slim
  workdir: /app
  app_src: .
  app_dst: /app
  expose_ports: ["5000"]
  start:
    mode: cmd
    cmd: gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app
```

## 常见坑

1. 监听地址写成 `127.0.0.1` 导致外部端口不通。
2. 未设置线程限制变量，在高核心服务器上触发 OpenBLAS 线程创建失败。
3. 依赖安装未使用 `--no-cache-dir` 导致镜像体积膨胀。

# Python 模板说明（最小可运行）

## 适用场景
- Flask / FastAPI / Django / 原生 HTTP 单服务题目。
- 通过 `exec` 前台运行 Python 进程。

## 默认约定
- 默认基础镜像：`python:3.11-slim`
- 默认工作目录：`/app`
- 默认端口：`5000`
- 默认启动命令：`python app.py`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `python:3.11-slim` | 基础镜像 |
| `{{WORKDIR}}` | 是 | `/app` | 工作目录 |
| `{{APP_SRC}}` | 是 | `.` | 应用来源路径 |
| `{{APP_DST}}` | 是 | `/app` | 应用目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `5000` | 暴露端口 |
| `{{START_CMD}}` | 是 | `python app.py` | 主进程命令 |
| `{{PIP_REQUIREMENTS_BLOCK}}` | 否 | 自动生成 | 依赖安装片段（含 `--no-cache-dir`） |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 片段 |

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "python-flask-basic"
  stack: "python"
  base_image: "python:3.11-slim"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["5000"]
  start:
    mode: "cmd"
    cmd: "python app.py"
```

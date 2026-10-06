# Node 模板说明（最小可运行）

## 适用场景
- Node 原生 http / Express / Koa / Fastify 单服务题目。
- 以 `exec` 前台运行主进程，避免容器假活。

## 默认约定
- 默认基础镜像：`node:20-alpine`（更小）；兼容性优先可改为 `node:20-slim`。
- 默认工作目录：`/app`
- 默认端口：`3000`
- 默认启动命令：`node server.js`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `node:20-alpine` | 运行时基础镜像 |
| `{{WORKDIR}}` | 是 | `/app` | 容器工作目录 |
| `{{APP_SRC}}` | 是 | `.` | 构建上下文内应用路径 |
| `{{APP_DST}}` | 是 | `/app` | 应用复制目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `3000` | Dockerfile `EXPOSE` 端口 |
| `{{START_CMD}}` | 是 | `node server.js` | `start.sh` 执行命令 |
| `{{NPM_INSTALL_BLOCK}}` | 否 | 自动生成 | 依赖安装逻辑（npm ci/npm install） |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量注入片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 指令片段 |

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "node-basic"
  stack: "node"
  base_image: "node:20-alpine"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["3000"]
  start:
    mode: "cmd"
    cmd: "node server.js"
```

## 常见问题
- 若有原生模块依赖，`node:20-alpine` 可能需要额外编译工具，可切换 `node:20-slim`。
- 不允许用 `sleep infinity` 或空转循环保持容器存活。

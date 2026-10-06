# Java(JAR) 模板说明（最小可运行）

## 适用场景
- 目录中已经准备好可运行 JAR（例如 `app.jar`）。
- 容器仅负责运行，不做编译。

## 默认约定
- 默认基础镜像：`eclipse-temurin:17-jre-jammy`
- 默认工作目录：`/app`
- 默认端口：`8080`
- 默认启动命令：`java -jar app.jar`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `eclipse-temurin:17-jre-jammy` | Java 运行时镜像 |
| `{{WORKDIR}}` | 是 | `/app` | 工作目录 |
| `{{APP_SRC}}` | 是 | `.` | 应用来源路径 |
| `{{APP_DST}}` | 是 | `/app` | 应用目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `8080` | 暴露端口 |
| `{{START_CMD}}` | 是 | `java -jar app.jar` | 主进程命令 |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 片段 |

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "java-jar-basic"
  stack: "java"
  base_image: "eclipse-temurin:17-jre-jammy"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["8080"]
  start:
    mode: "cmd"
    cmd: "java -jar app.jar"
```

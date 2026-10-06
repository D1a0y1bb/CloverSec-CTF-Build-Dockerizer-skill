# Tomcat(WAR) 模板说明（最小可运行）

## 适用场景
- 题目提供 `ROOT.war` 或 Tomcat WebApp 目录。
- 采用 `catalina.sh run` 前台运行，符合容器主进程要求。

## 默认约定
- 默认基础镜像：`tomcat:9.0-jre17-temurin-jammy`
- 默认工作目录：`/usr/local/tomcat`
- 默认端口：`8080`
- 默认启动命令：`catalina.sh run`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `tomcat:9.0-jre17-temurin-jammy` | Tomcat 基础镜像 |
| `{{WORKDIR}}` | 是 | `/usr/local/tomcat` | 工作目录 |
| `{{APP_SRC}}` | 是 | `ROOT.war` 或 `.` | 应用来源路径 |
| `{{APP_DST}}` | 是 | `/usr/local/tomcat/webapps/ROOT.war` | 应用目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `8080` | 暴露端口 |
| `{{START_CMD}}` | 否 | `catalina.sh run` | 主进程命令 |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 片段 |

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "tomcat-war-basic"
  stack: "tomcat"
  base_image: "tomcat:9.0-jre17-temurin-jammy"
  workdir: "/usr/local/tomcat"
  app_src: "ROOT.war"
  app_dst: "/usr/local/tomcat/webapps/ROOT.war"
  expose_ports: ["8080"]
  start:
    mode: "cmd"
    cmd: "catalina.sh run"
```

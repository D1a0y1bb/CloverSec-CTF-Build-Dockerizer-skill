# tomcat

兼容目录：保留旧路径的 Tomcat WAR 示例。

目录包含 `ROOT.war`，可直接渲染并构建镜像。

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
```

# Verification v3

`ctfctl.py verify` 按以下顺序执行：

1. 检查 Docker daemon。
2. 构建交付目录。
3. 以 `/start.sh` 启动容器。
4. 检查容器进程是否保持运行。
5. 按 `flag.mode` 执行 Flag 验证。
6. 执行 HTTP、TCP 或容器内探测。
7. 自动清理本次创建的容器。

验证报告分开记录：

- `build`：镜像是否构建成功。
- `runtime`：`/start.sh` 是否启动真实服务。
- `flag`：题目是否能读取本次写入的值。
- `probe`：题目入口是否返回预期结果。

静态 `validate.sh` 不能替代真实验证。

没有 Docker daemon 时，结果必须是 `environment_failed`。

没有题目探测配置时，结果可以是 `partial`，不能伪装成完整验收。

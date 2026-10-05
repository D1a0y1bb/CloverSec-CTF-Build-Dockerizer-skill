# Verification v3

`ctfctl.py verify` 按以下顺序执行：

1. 检查 Docker daemon。
2. 构建交付目录镜像。
3. 按镜像自身的 `CMD` 或 `ENTRYPOINT` 启动容器。
4. 等待容器保持运行，并读取状态或健康状态。
5. 按 `flag.mode` 执行 Flag 验证。
6. 执行声明的 HTTP、TCP、容器内探测和可选 `smoke_assert.sh`。
7. 自动清理本次创建的容器。

验证报告分开记录：

- `build`：镜像是否构建成功。
- `runtime`：`/start.sh` 是否启动真实服务。
- `flag`：题目是否能读取本次写入的值。
- `probe`：题目入口是否返回预期结果。
- `smoke_assert`：题目目录提供的额外业务断言是否通过。

静态 `validate.sh` 不能替代真实验证。

没有 Docker daemon 时，结果必须是 `environment_failed`。

没有题目探测配置时，结果只证明容器和 Flag 合同。非 `direct_exec` Flag 没有执行题目专用更新命令时，结果保持 `partial`。

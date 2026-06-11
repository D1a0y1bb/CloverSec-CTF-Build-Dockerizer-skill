# python-flask-basic

最小 Flask 示例，用于验证 Python 栈模板的可运行性。

本目录也是 `challenge.verification.solve_probe` 的官方示例。业务入口验证会在容器启动后读取 `challenge.yaml` 里的 HTTP probe，确认题目入口返回 `hello from python-flask-basic`。

## 运行步骤

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-python-flask-basic:latest .
docker run -d -p 5001:5000 ctf-python-flask-basic:latest /start.sh
```

只验证本示例的业务入口断言时，在 Skill 根目录执行：

```bash
bash scripts/smoke_test.sh --case python-flask-basic
```

该命令会读取本目录 `challenge.yaml` 里的 `challenge.verification.solve_probe`，并检查 HTTP 响应包含 `hello from python-flask-basic`。

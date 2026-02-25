# rdg-python-ssti-basic

RDG(Python) 最小回归样例，用于验证：

- `stack: rdg` + Python 入口推断
- `python app.py` 前台主服务可执行
- RDG ttyd 配置字段可解析并注入模板

## 本地验证

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t rdg-python-ssti-basic:latest .
docker run -d -p 18081:80 rdg-python-ssti-basic:latest /start.sh
```

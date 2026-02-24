# python-flask-basic

最小 Flask 示例，用于验证 Python 栈模板的可运行性。

## 运行步骤

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-python-flask-basic:latest .
docker run -d -p 5001:5000 ctf-python-flask-basic:latest /start.sh
```

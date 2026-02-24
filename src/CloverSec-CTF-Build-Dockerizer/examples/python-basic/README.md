# python-basic

最小 Python HTTP 示例。

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-python-basic:latest .
docker run -d -p 5002:5000 ctf-python-basic:latest /start.sh
```

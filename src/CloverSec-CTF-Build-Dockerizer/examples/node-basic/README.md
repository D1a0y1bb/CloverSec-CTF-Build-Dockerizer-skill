# node-basic

最小 Node HTTP 示例。

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-node-basic:latest .
docker run -d -p 3001:3000 ctf-node-basic:latest /start.sh
```

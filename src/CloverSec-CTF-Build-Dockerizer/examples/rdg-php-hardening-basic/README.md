# rdg-php-hardening-basic

RDG(PHP) 最小回归样例，用于验证：

- `stack: rdg` 渲染路径可用
- `apache2-foreground` 前台主服务可执行
- ttyd 缺失时仅告警，不阻断

## 本地验证

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t rdg-php-hardening-basic:latest .
docker run -d -p 18080:80 rdg-php-hardening-basic:latest /start.sh
```

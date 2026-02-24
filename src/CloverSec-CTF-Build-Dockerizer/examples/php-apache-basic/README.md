# php-apache-basic

最小 PHP + Apache 示例，目标是验证：

- `render.py` 可生成 Dockerfile/start.sh/flag
- `validate.sh` 无 ERROR
- `docker run ... /start.sh` 可稳定前台运行 Apache

## 运行步骤

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-php-apache-basic:latest .
docker run -d -p 8081:80 ctf-php-apache-basic:latest /start.sh
```

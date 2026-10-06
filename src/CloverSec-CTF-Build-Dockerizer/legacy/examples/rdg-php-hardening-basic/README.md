# rdg-php-hardening-basic

RDG(PHP) 最小回归样例，用于验证：

- `stack: rdg` 渲染路径可用
- `apache2-foreground` 前台主服务可执行
- 默认 `ttyd + sshd` 登录链路与 `ctf/123456`
- `check_service` 真实检查可执行（`check/check.sh`，健康检查 + 反序列化负向检查）

## 本地验证

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t rdg-php-hardening-basic:latest .
docker run -d -p 18080:80 rdg-php-hardening-basic:latest /start.sh
bash check/check.sh 127.0.0.1 18080
```

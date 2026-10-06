# lamp-basic

最小 LAMP 示例，包含：

- `index.php`：基础页面
- `init.sql`：数据库初始化 SQL 示例（可编码为 `MYSQL_INIT_SQL_B64` 注入）
- `challenge.yaml`

## 运行步骤

```bash
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-lamp-basic:latest .
docker run -d -p 8082:80 ctf-lamp-basic:latest /start.sh
```

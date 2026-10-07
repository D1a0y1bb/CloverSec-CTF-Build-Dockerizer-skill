# 题目手册

手册写在 `<题目类型-题目名称>/README/<题目类型-题目名称>.md`，截图放同目录的 `assets/`，正文用相对路径引用：`![截图](assets/image-20261007112926.png)`。

## 骨架

```markdown
# Web-残影

### 1.1 题目名称

残影

### 1.2 题目描述

凌晨三点，图片审核台收到了一张"只存在一瞬"的 GIF。你能在这道残影彻底消失前抓住它吗？

### 1.3 题目难度

中等

### 1.4 考察信息

Nginx location 匹配优先级、PHP-FPM 路径截断、文件上传 TOCTOU 竞态、pcntl 绕过 disable_functions

### 1.5 旗帜信息

动态 Flag。原始静态 Flag `flag{placeholder}`。

平台覆盖方式：`echo "$new_flag" > /flag`

Flag 文件位置：`/flag`

### 1.6 题目情况

服务监听 80。上传的 GIF 经过 Nginx 与 PHP-FPM 两层处理，竞态窗口约 300 毫秒。

### 1.7 部署方式

```bash
docker buildx build --platform=linux/amd64 . -t afterimage:latest --load
docker run -d -p 8080:80 afterimage:latest /start.sh
```

检查服务：

```bash
curl -i http://localhost:8080/
```

### 1.8 题目设计

1. 选手上传一个 GIF，服务在两秒后删除；
2. 删除前 Nginx 已经把请求交给 PHP-FPM；
3. ...

### 1.9 解题步骤

连接服务：

```bash
nc -nv HOST PORT
```

预期输出：

```text
[INFO] ready
```

**常见失败现象和定位方法**

`ERR interp memory access` 连续出现：正常热身过程，继续等待。

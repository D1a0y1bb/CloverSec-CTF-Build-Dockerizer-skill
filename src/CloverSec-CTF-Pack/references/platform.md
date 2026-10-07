# 平台合同与 challenge.yaml

## 目录

- 平台怎么跑题目
- 用环境变量传 Flag 的平台
- 镜像 tar 的格式
- Flag 路径与写入方式
- challenge.yaml 字段

## 平台怎么跑题目

1. 用 Dockerfile 构建 `linux/amd64` 镜像。在 Apple Silicon 上构建要加 `--platform linux/amd64`，否则导出的镜像在平台上起不来。
2. `docker run -d -p <映射> <镜像> /start.sh` 启动。`/start.sh` 覆盖 `CMD`；`ENTRYPOINT` 不为空时 `/start.sh` 会变成它的参数，官方 php、nginx、node 镜像的 `docker-*-entrypoint` 会原样执行参数，不受影响。
3. 容器起来后，平台以 root 执行：

   ```bash
   docker exec <容器> sh -c 'printf "%s\n" "$1" > "$2"' sh "$new_flag" "$flag_path"
   ```

   所以镜像里要有 `sh`，`flag.path` 的目录要存在。distroless、scratch 镜像不能直接用。
4. 选手访问映射出来的端口，服务要监听 `0.0.0.0`。

## 用环境变量传 Flag 的平台

GZCTF、DASCTF 等平台在 `docker run` 时用环境变量传 Flag（`GZCTF_FLAG`、`DASFLAG`、`FLAG`），不会再执行写文件的命令。题目要在这类平台上用时，start.sh 开头加一段：

```bash
# 平台用环境变量传 Flag 时写进 flag.path，写完清掉变量，选手读 /proc/1/environ 拿不到。
FLAG_VALUE="${GZCTF_FLAG:-${DASFLAG:-${FLAG:-}}}"
if [ -n "$FLAG_VALUE" ]; then
    printf '%s\n' "$FLAG_VALUE" > /flag
    unset GZCTF_FLAG DASFLAG FLAG FLAG_VALUE
fi
```

四叶草平台不传这些变量，这段不会执行。只为四叶草平台出的题不需要加。

## 镜像 tar 的格式

交付镜像用 `docker save`，导入用 `docker load`：

```bash
docker buildx build --platform linux/amd64 -t afterimage:latest --load .
docker save afterimage:latest -o 残影.tar
```

有些平台只接受 `docker export` 导出的文件系统 tar（`docker import` 导入）。这种格式不保留 `WORKDIR`、`ENV`、`EXPOSE`、`CMD`，start.sh 里要自己 `cd` 到绝对路径、自己 `export` 需要的环境变量，不能依赖 Dockerfile 里的设置。

## Flag 路径与写入方式

### 常用路径

| 路径 | 典型题型 |
|---|---|
| `/flag` | Web、AI、Misc 大多数 |
| `/home/ctf/flag` | Pwn |
| `/root/flag` | 主机安全、应急响应 |
| `/var/www/html/flag` | PHP 直接 include 或 readfile |
| `/var/www/html/flag.php` | Flag 写在 PHP 文件里 |

路径填错，平台写入的 Flag 程序读不到。

### 直接写文件

- Dockerfile 用 `COPY flag <flag.path>` 放占位文件，Web 题 `chmod 444`，Pwn 题 `root:ctf 440`。
- 程序每次请求时读取 Flag 文件。
- start.sh 不创建、不覆盖、不 chmod Flag 文件。

### 文件替换和数据库 Flag

把平台要执行的命令写进题目手册，不另写脚本：

```bash
# Flag 写在 PHP 文件里
sed -i "s/$flag/$new_flag/g" /var/www/html/flag.php

# Flag 存在数据库里，等 MySQL 就绪后更新
/usr/bin/wait-for-it.sh 127.0.0.1:3306 -- \
  mysql -e "USE ctf; UPDATE flag_tab SET flag='$new_flag' WHERE id=1;" -uroot -proot
```

### Flag 缓存

服务启动时把 Flag 读进内存，平台之后改了文件也不会生效：

```python
# 错误：进程启动时读一次
FLAG = open("/flag").read()

# 正确：每次请求时读
def get_flag():
    return open("/flag").read()
```

Java 的 `static { flag = readFile(); }` 同理。`verify.sh --solve` 用随机测试 Flag 验证，缓存的题会判为 failed。

## challenge.yaml 字段

```yaml
challenge:
  name: afterimage              # 题目标识，kebab-case
  stack: php                    # php / node / python / java / static / pwn
  base_image: php:8.1-fpm-alpine
  workdir: /var/www/html        # 容器内工作目录
  app_src: src                  # 源码在交付目录里的位置
  app_dst: /var/www/html        # 源码 COPY 到容器的目标
  expose_ports: ["80"]          # 对外端口，字符串数组
  start:
    mode: cmd
    cmd: "nginx -g 'daemon off;'"   # start.sh 最后 exec 的主进程
  platform:
    entrypoint: /start.sh
    require_bash: true          # start.sh 用到 bash 语法时写 true
    docker_platform: linux/amd64  # 只能在 amd64 运行的题（Pwn、x86 二进制）写上
  flag:
    path: /flag                 # 程序实际读取的路径
    permission: "444"
```

不知道的字段不写，填错比不填更麻烦。verify.sh 读取 `expose_ports` 和 `flag.path`，两种写法都支持：

```yaml
expose_ports: ["80", "22"]
expose_ports:
  - "80"
```

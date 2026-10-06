# 平台合同与 challenge.yaml

## 平台怎么跑你的题

四叶草竞赛平台对每道容器题的约定很简单：

1. 平台用你的 `Dockerfile` 构建镜像（通常是 `linux/amd64`）。
2. 平台以 `/start.sh` 为入口启动容器：`docker run -d -p <映射> <image> /start.sh`。
3. `/start.sh` 必须**前台**拉起真实服务，并作为容器主进程（PID 1）。不能空转保活（`tail -f`、`sleep infinity` 这类是错的）。
4. 容器起来后，平台把这一场的**动态 Flag 直接写进** `challenge.yaml` 里 `flag.path` 指定的文件，然后选手才开始解。

所以你要保证的就三件事：镜像能构建、`/start.sh` 能起真服务、`flag.path` 指对程序真正读取 Flag 的那个文件。

## Flag 怎么处理

### 真实 Flag 路径分布（从题库实际抽样）

| 路径 | 典型题型 |
|---|---|
| `/flag` | Web、AI、Misc 大多数 |
| `/home/ctf/flag` | Pwn（固定约定，选手 exploit 后 cat 读取） |
| `/root/flag` | 部分主机安全/应急响应题 |
| `/data/flag` | 少数特殊场景 |
| `/var/www/html/flag` | PHP 直接 include 或 readfile |
| `/var/www/html/flag.php` | PHP 题 flag 嵌在 PHP 文件里 |

**写对路径是最重要的一件事**，填错了平台写的 flag 程序读不到。

### 平台的动作

绝大多数题是"直接写文件"——平台起容器后直接覆盖 `flag.path`：

```bash
echo "$new_flag" > /flag          # 平台侧动作，你不用写这个脚本
```

你要做的：
- Dockerfile 里 `COPY flag /flag` 放一个初始占位，`chmod 444 /flag`。
- 程序从 `flag.path` **每次请求时**读取 Flag，不能启动时缓存一次（下面说原因）。
- `start.sh` 不要碰 Flag（不 touch、不覆盖、不同步）。

### 文件替换和数据库 Flag

只在 `challenge.yaml` 和题目手册里记真实命令即可，不要造通用脚本：

```bash
# PHP 文件里嵌着 flag 常量，平台用 sed 替换
sed -i "s/$flag/$new_flag/g" /var/www/html/flag.php

# 数据库里存 flag，平台等 MySQL 就绪后更新
/usr/bin/wait-for-it.sh 127.0.0.1:3306 -- \
  mysql -e "USE ctf; UPDATE flag_tab SET flag='$new_flag' WHERE id=1;" -uroot -proot
```

### 常见陷阱：Flag 缓存

从题库反复出现的坑——服务启动时把 flag 读进内存，平台改了文件没用：

```python
# 错误：模块级变量，Python 进程启动时读一次，之后 /flag 被平台覆盖也还是旧值
FLAG = open("/flag").read()

# 正确：每次请求时读，动态 flag 生效
def get_flag():
    return open("/flag").read()
```

Java 静态初始化块（`static { flag = readFile(); }`）同理，要改成方法调用。

## challenge.yaml 字段

```yaml
challenge:
  name: afterimage              # 题目标识，kebab-case
  stack: php                    # php/node/python/java/static/c，决定基础镜像风格
  base_image: php:8.1-fpm-alpine
  workdir: /var/www/html        # 容器内工作目录
  app_src: src                  # 源码在交付目录里的位置
  app_dst: /var/www/html        # 源码 COPY 到容器的目标
  expose_ports: ["80"]          # 对外端口，字符串数组
  start:
    mode: cmd
    cmd: "nginx -g 'daemon off;'"   # start.sh 最终 exec 的主进程
  platform:
    entrypoint: /start.sh       # 固定 /start.sh
    require_bash: true          # 仅当 start.sh 用到 bash 特性时写 true，纯 sh 可省
  flag:
    path: /flag                 # 程序真正读取 Flag 的路径
    permission: "444"
```

字段只填题目真实需要的。没有的别硬凑，留空或省略比填错值好。多服务、Scenario 等复杂字段见 `special.md`。

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
  category: Web                 # 20 个题目类型之一
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
    legacy_env: FLAG            # 旧平台用环境变量传值时写上变量名
provenance:
  status: original_adapter
  original_material: [源码, install.sql]
  missing: []
  preserved: [漏洞类型=文件上传 TOCTOU, 链路=3 步]
  simplified: []
  env_limited: ""
  verify: passed
```

不知道的字段不写，填错比不填更麻烦。verify.sh 读取 `expose_ports` 和 `flag.path`，两种写法都支持：

```yaml
expose_ports: ["80", "22"]
expose_ports:
  - "80"
```

## provenance：题目来源与恢复状态

`provenance` 是必填字段，用来把"容器能跑"和"题目是原题还是重建的"分开。只看 `passed` 会把"能跑"误读成"题目完成"。

| 字段 | 说明 |
|---|---|
| `status` | `original_adapter`（原题材料完整，只补平台合同）/ `independent_completion`（材料缺失后独立重建）/ `incomplete`（材料缺失且没等价恢复）/ `attachment_only`（纯附件题） |
| `original_material` | 手里有的原始材料，列文件名 |
| `missing` | 缺的材料，列清楚 |
| `preserved` | 保留下来的原题特征：漏洞类型、链路步数、要绕过的防护 |
| `simplified` | 相对原题简化了什么。有值必须写清为什么无法等价恢复。没有就写 `[]` |
| `env_limited` | 本机环境限制，例如 `Apple ARM64 模拟下无法执行原始 rt_sigreturn`。这是环境问题，不是改题的理由 |
| `verify` | 验证结论：`passed` / `environment_failed` / `incomplete` |

规则：

- `status: incomplete` 的题**不许**在手册或交付说明里写成"已验证通过"。
- `independent_completion` 必须在手册 1.8 里写明这是独立补全，不是原题还原。
- `simplified` 有值时，这道题已经偏离原题难度，要在交付说明里单独告诉用户。

## RDG 相关字段

```yaml
challenge:
  category: RDG
  profile: rdg
  expose_ports: ["80", "8022"]
  flag:
    path: /flag
    permission: "444"
    legacy_env: FLAG          # 旧平台通过环境变量传 Flag 时写
  check:
    enabled: true
    path: check/check.sh
  verification:
    solve_probe:
      type: http
      path: /            # 服务可用性探测路径，根路径 403/404 时指定真实入口
      expect_status: 200
      expect_text: "版权所有 ©2015-2024"
```

- `check.enabled: true` 时 `verify.sh` 走 RDG 判定：先跑一遍 check 确认初始环境报"有漏洞"，再验证容器生命周期。
- **不需要动态 Flag 的 RDG 题**：敏感目标是自己配置里的固定内容时，`flag:` 块可以省掉，或在 `notes` 里注明 Flag 不是判据。check 直接验证那个固定目标还能不能被读到。
- ttyd 端口写进 `expose_ports`，`verify.sh` 会和 Web 端口一起探测。
- `notes` 写清 check 覆盖哪些关卡、初始环境的预期结果。

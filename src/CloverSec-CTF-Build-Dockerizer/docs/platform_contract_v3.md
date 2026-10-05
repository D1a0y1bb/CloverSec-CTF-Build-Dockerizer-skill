# Platform Contract v3

## 默认合同

普通题目默认使用 `direct-exec-v1`。

平台执行：

```bash
docker run -d <image> /start.sh
docker exec <container> sh -c 'printf "%s\n" "$1" > "$2"' sh "$new_flag" "$flag_path"
```

`/start.sh` 是唯一默认启动入口。

`flag.path` 是题目程序实际读取的路径。

`/flag` 只是默认路径，不是平台硬编码路径。

## Flag 模式

| 模式 | 用途 | 默认行为 |
|---|---|---|
| `direct_exec` | 平台直接写文件 | 不生成 `changeflag.sh` |
| `file_replace` | PHP、配置文件等替换 | 输出 `FLAG_UPDATE.md` 命令 |
| `database` | MySQL、MariaDB、Redis 等 | 输出等待命令和 SQL |
| `helper_script` | 旧平台兼容 | 生成并验证 `changeflag.sh` |
| `qemu_guest` | Linux-QEMU guest rootfs | 使用专用 guest 注入流程 |

## 启动脚本规则

- `start.sh` 必须可执行。
- `start.sh` 必须启动真实服务。
- 单服务使用 `exec`。
- `start.sh` 不初始化通用 Flag。
- `start.sh` 不覆盖平台注入的 Flag。
- 多服务题目必须保留真实前台服务和明确启动顺序。

## 交付目录

普通题目可以只包含：

```text
Dockerfile
start.sh
src/ 或 app/
flag                    # 仅在初始文件需要时存在
challenge.yaml          # 可选，但推荐保留
FLAG_UPDATE.md
VERIFY.md
delivery-manifest.json
```

`changeflag.sh` 只在合同明确要求时存在。

## 结果状态

- `passed`：当前阶段的所有必要检查通过。
- `failed`：代码或交付文件检查失败。
- `partial`：部分检查通过，仍有未完成证据。
- `environment_failed`：Docker、架构或外部环境阻塞。
- `not_reproduced`：没有执行足够的真实步骤。
- `unverified`：缺少必要事实，不能安全推断。

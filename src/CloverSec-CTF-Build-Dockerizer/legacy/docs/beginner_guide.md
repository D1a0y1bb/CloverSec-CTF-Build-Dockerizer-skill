# 普通题目使用指南

本文只介绍默认的 clean profile。

## 你需要提供什么

你可以提供以下任意一种输入：

- 题目想法和技术栈。
- 一部分源码。
- 一个已有 Dockerfile 或 start.sh 的目录。
- 一个包含源码、手册和附件的历史题目目录。

输入目录不会被默认覆盖。输出目录默认是 `<题目目录>/dist`。

## 默认命令

```bash
python3 scripts/ctfctl.py inspect --project-dir <题目目录> --format json
python3 scripts/ctfctl.py scaffold --project-dir <题目目录> --output <题目目录>/dist --profile clean
python3 scripts/ctfctl.py build --project-dir <题目目录>/dist --image cloversec/local-challenge:dev
python3 scripts/ctfctl.py verify --project-dir <题目目录>/dist --format json
python3 scripts/ctfctl.py package --project-dir <题目目录>/dist --output <题目目录>/challenge.tar.gz
```

`inspect` 读取事实。

`scaffold` 生成交付目录。

`build` 只执行 Docker build，并把结果写入 `.ctfbuild/build.json`。

`verify` 执行 Docker run、Flag 回读、声明的入口探测和可选 `smoke_assert.sh`。

`package` 生成发布归档。

## 默认目录

```text
dist/
├── src/
├── Dockerfile
├── start.sh
├── challenge.yaml
├── .dockerignore
└── .ctfbuild/
    ├── audit.json
    ├── verify.json              # verify 执行后生成
    ├── delivery-manifest.json
    └── verification.md
```

`changeflag.sh` 只在旧 helper 或 Linux-QEMU 合同中生成。

`FLAG_UPDATE.md` 不属于 clean profile 的根目录。

文件替换题和数据库题的更新说明写入 `.ctfbuild/flag-update.md`。

## Flag 配置

普通题目使用 direct-exec：

```yaml
flag:
  mode: direct_exec
  path: /var/www/html/flag.php
```

`flag.path` 必须是程序实际读取的路径。

`/flag` 不是平台固定路径。

文件替换题使用：

```yaml
flag:
  mode: file_replace
  path: /var/www/html/flag.php
  update:
    command: sed -i "s/$flag/$new_flag/g" /var/www/html/flag.php
```

数据库题把 SQL 和必要的等待地址写入 `flag.update`。

不要在 `start.sh` 中初始化通用 Flag。

## 缺少信息时怎么办

如果没有可靠的端口、启动命令、基础镜像或 Flag 路径，Skill 不会猜测。

它会输出 `partial` 或 `unverified`。

它会只询问完成下一步所需的信息。

## 高级题目

以下输入需要读取对应资料：

- compose 或 Vulhub-like：`data/scenario_schema.md`。
- Scenario：`docs/advanced_routing.md`。
- Bundle：`docs/bundle_design.md`。
- RDG/SecOps：`docs/validation_guide.md`。
- Linux-QEMU：`docs/linux_qemu_manual_validation.md`。
- 旧平台 helper：`docs/legacy_migration.md`。

不要为了普通单服务题目读取全部高级资料。

# Core delivery contract

本文只描述普通单服务题目的默认行为。高级场景必须按输入证据路由。

## 输入

Skill 可以接收以下输入：

- 题目想法和运行要求。
- 只有部分源码的目录。
- 已有 Dockerfile、start.sh 或 challenge.yaml 的目录。
- 历史题目目录、源码目录和附件混合目录。

先保留原始输入。默认把整理结果写入 `dist/` 或用户指定的独立目录。原始输入目录保持不变。

## 默认输出

```text
challenge/
├── src/
├── Dockerfile
├── start.sh
├── challenge.yaml
├── .dockerignore
└── flag
```

`flag` 只在题目启动前需要初始文件时存在。

普通题目不在根目录生成以下文件：

- `changeflag.sh`
- `FLAG_UPDATE.md`
- `VERIFY.md`
- `delivery-manifest.json`

审计、合同、验证和归档信息写入 `.ctfbuild/`。其中包括 `audit.json`、`verify.json` 和 `delivery-manifest.json`。归档文件写入 `dist/`。

## 源码整理

保留运行需要的源码、依赖、静态资源和二进制文件。

`clean` 模式移除或忽略以下内容：

- `node_modules/`、`__pycache__/`、构建缓存和旧 `dist/`。
- 题目手册、选手附件和发布压缩包。
- 旧验证报告和机器生成清单。
- 不参与运行的 compose 编排文件、停止脚本和明确的作者工具。

如果已有 `src/`，保留它的内容。

如果输入是源码散落在根目录的新题目，将运行源码整理到 `src/`。

如果已有 Dockerfile 依赖特定路径，先保留路径，再通过合同检查报告问题。

`preserve` 模式不执行上述主动清理。`legacy` 模式允许旧 helper 和旧版报告文件。

## 统一命令

普通单服务只需要以下入口：

```text
inspect → scaffold → build → verify → package
```

`inspect` 读取事实。`scaffold` 生成目录。`build` 只构建镜像。`verify` 启动容器并执行 Flag、入口和可选 smoke 检查。`package` 把交付目录归档到目录外。

输入缺少 `challenge.yaml` 但已经存在 Dockerfile 时，`scaffold` 根据 Dockerfile、启动脚本和 Flag 文件生成最小合同。它不会猜测业务数据库更新命令。

## Flag

普通题目使用 `direct_exec`。

```yaml
flag:
  mode: direct_exec
  path: /challenge/flag.txt
```

文件替换题和数据库题使用 `flag.update` 保存真实业务更新方式。

不要把通用 Flag 写入 `start.sh`。

只有 `helper_script`、旧平台合同或 `qemu_guest` 允许出现 `changeflag.sh`。

## 交付卡

完成后只报告当前任务需要的信息：

```text
status: passed|partial|failed|environment_failed|not_reproduced|unverified
output: <交付目录>
source: <源码根>
entrypoint: /start.sh
ports: <端口列表>
flag: <mode> <path>
verified: <已执行的真实检查>
pending: <未执行检查和原因>
```

不要把长篇审计 JSON 直接作为用户交付说明。

## 缺少事实

缺少端口、启动命令、基础镜像或真实 Flag 路径时，保留 `partial` 或 `unverified`。

一次只提出完成下一步所需的问题。

不要根据文件名猜测服务端口、Flag 路径或数据库更新命令。

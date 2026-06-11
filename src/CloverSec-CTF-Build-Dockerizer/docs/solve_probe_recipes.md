# solve_probe 示例片段

`challenge.verification.solve_probe` 用于 smoke 阶段验证题目入口。它不在 `validate.sh` 中执行；执行入口是：

```bash
bash scripts/smoke_test.sh --case <example-name>
```

内置示例：

```bash
bash scripts/smoke_test.sh --case python-flask-basic
```

## HTTP 页面断言

适合 Web 题、登录页、首页 banner、接口健康检查。

```yaml
verification:
  solve_probe:
    type: http
    path: /
    expect_status: 200
    expect_text: "Welcome"
```

如果需要检查登录页：

```yaml
verification:
  solve_probe:
    type: http
    path: /login
    expect_status: 200
    expect_text: "password"
```

## TCP banner 断言

适合 nc 服务、简单 Pwn 服务、Redis/MySQL 前的端口可达检查。

```yaml
verification:
  solve_probe:
    type: tcp
    expect_text: "name:"
```

该检查只证明服务入口可达，不证明漏洞可利用。

## 容器内命令断言

适合服务没有稳定 HTTP/TCP 文本输出，但可以在容器内检查进程、文件或业务路径。

```yaml
verification:
  solve_probe:
    type: container_exec
    cmd: "bash -lc 'test -f /flag && pgrep -fa python'"
    expect_exit: 0
```

检查动态 flag 同步路径：

```yaml
verification:
  solve_probe:
    type: container_exec
    cmd: "bash -lc 'test \"$(cat /home/ctf/flag)\" = \"$(cat /flag)\"'"
    expect_exit: 0
```

## Pwn nc 入口

Pwn 题通常要人工确认程序真实读取的 flag 路径。`flag.sync_paths` 负责把平台动态 flag 同步到业务路径，`solve_probe` 只验证入口有响应。

```yaml
flag:
  path: /flag
  permission: "444"
  sync_paths:
    - /home/ctf/flag

verification:
  solve_probe:
    type: tcp
    expect_text: "choice"
```

如果源码读取 `flag0` 或 `flag1`，不要只保留默认 `/home/ctf/flag`：

```yaml
flag:
  path: /flag
  permission: "444"
  sync_paths:
    - /home/ctf/flag0
    - /home/ctf/flag1
```

源码中的相对路径要按题目进程的 WORKDIR 转成绝对路径。不要把 `flag0` 这类相对路径直接写进 `sync_paths`，因为 `/changeflag.sh` 执行时的当前目录不一定是题目 WORKDIR。

## 动态 flag 与真实拿 flag

如果要证明“题目入口能拿到动态 flag”，不要只写端口检查。推荐写题目特定断言：

```yaml
verification:
  solve_probe:
    type: container_exec
    cmd: "bash -lc '/opt/challenge/solve_probe.sh'"
    expect_exit: 0
```

`solve_probe.sh` 应由题目作者维护，内容可以执行 PoC、请求业务入口或检查动态 flag 输出。复杂交互题不要把 PoC 逻辑硬塞进通用模板。

# 架构总览

系统分成默认单服务链路和按需高级链路。

## 默认单服务链路

```text
题目输入
  │
  ▼
ctfctl.py inspect
  │
  ▼
ctfctl.py scaffold --profile clean
  │
  ├── src/
  ├── Dockerfile
  ├── start.sh
  └── challenge.yaml
  │
  ▼
ctfctl.py verify
  │
  ├── 静态合同
  ├── Docker build/run
  ├── Flag 回读
  └── HTTP/TCP 入口探测
```

`ctfctl.py` 是普通题目的模型入口。

## 输入层

- `data/schema.md`：`challenge.yaml` 输入契约。
- `data/stacks.yaml`：栈默认值和探测特征。
- `data/patterns.yaml`：端口和启动命令线索。
- `data/runtime_profiles.yaml`：运行时档位映射。

## 生成层

- `scripts/ctfctl.py`：审计、脚手架、真实验证和归档。
- `scripts/render.py`：已确认合同的底层渲染入口。
- `templates/<stack>/`：栈模板。
- `templates/snippets/`：Flag、healthcheck 和防御片段。

## 校验层

- `scripts/validate.sh`：平台硬规则和合同检查。
- `scripts/smoke_test.sh`：业务入口断言。
- `scripts/validate_scenario.py`：Scenario 服务检查。
- `scripts/linux_qemu_manual_check.sh`：Linux-QEMU 分级检查。

## 高级链路

Scenario、Bundle、RDG/SecOps 和 Linux-QEMU 保留独立入口。

它们通过 `docs/advanced_routing.md` 触发。

它们不会改变普通题目的 direct-exec 默认合同。

## 机器证据

`scaffold` 将审计、验证和归档清单写入输出目录的 `.ctfbuild/`。

`package` 会排除 `.ctfbuild/`、缓存、手册和附件。

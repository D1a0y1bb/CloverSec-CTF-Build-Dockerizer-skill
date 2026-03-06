# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
  <span> · </span>
  <a href="README.ja.md"><strong>日本語</strong></a>
  <span> · </span>
  <a href="README.en.md"><strong>Legacy English Entry</strong></a>
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v2.0.0-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-11-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/profiles-jeopardy%2Frdg%2Fawd%2Fawdp%2Fsecops-16a34a?style=for-the-badge" alt="Profiles" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v2.0.0"><img src="https://img.shields.io/badge/release-zip%2Bsbom-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v2.0.0</code></p>

CloverSec-CTF-Build-Dockerizer is a delivery engine for CTF challenge containers across Jeopardy, RDG, AWD/AWDP-compatible profile workflows, SecOps hardening tracks, BaseUnit service images, and local Scenario orchestration.

## What's New in v2.0.0

- Enforced platform contract output: every render now emits `Dockerfile`, `start.sh`, and `changeflag.sh`.
- Introduced V2 config model: `challenge.profile` + `challenge.defense` as primary interface; legacy `challenge.rdg` still accepted.
- Added independent `stack=secops` and `stack=baseunit`.
- Added component renderer:
  - `data/components.yaml`
  - `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py`
- Added scenario pipeline:
  - `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py`
  - `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py`
  - `data/scenario_schema.md`
- Added AWDP patch contract scaffolding:
  - `patch/src/`
  - `patch/patch.sh`
  - `patch_bundle.tar.gz`
- Added full multilingual docs: English, Chinese, Japanese.

## Core Capability Matrix

| Capability | Entry | Purpose | Output |
|---|---|---|---|
| Auto proposal | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` | Infer stack, ports, start command, profile hints | `config_proposal` |
| Proposal parser | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | Convert `CONFIG PROPOSAL` into `challenge.yaml` | normalized config |
| Single challenge render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | Generate platform-ready delivery files | `Dockerfile/start.sh/changeflag.sh/(flag optional)` |
| BaseUnit render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | Build component+variant minimal units | standard delivery dir |
| Scenario render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | Render multi-service local scenario | service dirs + `docker-compose.yml` |
| Scenario validate | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | Validate mode/profile/ports/AWDP patch contract | static pass/fail |
| Contract validate | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | Enforce platform hard rules and policy checks | ERROR/WARN/INFO |
| Example regression | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | Batch regression on examples and scenarios | pass/fail summary |

## Quick Start

### 1) Render a challenge directory

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### 2) Render a BaseUnit component

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --output /tmp/baseunit-redis
```

### 3) Render a local AWD/AWDP scenario

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

## Platform Contract (V2)

Every render must satisfy:

- `/start.sh` exists and is executable.
- `/changeflag.sh` exists and is executable.
- `/bin/bash` is available in image.
- Dockerfile declares `EXPOSE`.
- `start.sh` launches real service processes (no idle keepalive patterns).

`/flag` behavior:

- default: required artifact
- optional only when `include_flag_artifact=false` in non-jeopardy defense profiles (commonly RDG/AWDP/SecOps check-service delivery)

## V2 Profiles and Defense

Supported profiles:

- `jeopardy`
- `rdg`
- `awd`
- `awdp`
- `secops`

V2 precedence:

- primary: `challenge.defense`
- compatibility: `challenge.rdg`
- render normalization maps both into one runtime behavior model

## BaseUnit Components (initial batch)

- `mysql`
- `redis`
- `sshd`
- `ttyd`
- `apache`
- `nginx`
- `tomcat`
- `php-fpm`
- `vsftpd`
- `weblogic`

Use `render_component.py --list` to inspect current variants.

## AWD/AWDP/Vulhub-like Boundary

`docker-compose.yml` generated by Scenario mode is **local orchestration output only**.

Platform final delivery remains per-service:

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

This keeps compatibility with target platforms that require single-container challenge units.

### Vulhub-like Migration Path

When migrating a Vulhub-style multi-service environment:

1. split each service into a single challenge folder or a `baseunit` component variant
2. express the service graph in `scenario.yaml`
3. render and validate locally with `render_scenario.py` + `validate_scenario.py`
4. deliver each rendered service directory independently to the target platform

Reference example (Vulhub-like migration demo):

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-vulhub-like-basic/scenario.yaml \
  --output /tmp/scenario-vulhub-like

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-vulhub-like
```

## AWDP Patch Workflow

For services rendered as `profile=awdp`, V2 enforces:

- `patch/src/`
- executable `patch/patch.sh`
- `patch_bundle.tar.gz` containing both entries above

## SecOps vs AWD (practical difference)

| Topic | AWD | SecOps |
|---|---|---|
| Goal | attack + maintain availability | hardening and config governance |
| Typical stack | web/pwn stacks + `profile=awd` | `stack=secops` + `profile=secops` |
| Login channel | usually enabled for operation | enabled/disabled per hardening policy |
| Scoring | service check or attack/defense platform logic | check-service and hardening checks |

## Validation and Release

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh
bash scripts/publish_release.sh --version v2.0.0
```

## Documentation Index

- Skill spec: `src/CloverSec-CTF-Build-Dockerizer/SKILL.md`
- Input schema: `src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- Platform contract: `src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- Architecture overview: `src/CloverSec-CTF-Build-Dockerizer/docs/architecture_overview.md`
- Stack cookbook: `src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- Scenario schema: `src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md`

## References

- [Vulhub](https://github.com/vulhub/vulhub)
- [Quick Start CTF mode docs](https://quickstart-ctf.github.io/quickstart/mode.html)
- [AWDP patch workflow reference (CN)](https://www.cn-sec.com/archives/1948396.html)

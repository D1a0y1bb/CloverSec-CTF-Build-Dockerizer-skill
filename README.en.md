# CloverSec-CTF-Build-Dockerizer

[简体中文](README.md)

[![Version](https://img.shields.io/badge/version-v1.2.4-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![CTF Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)

A delivery-focused Skill for CTF Jeopardy challenges (Web / Pwn / AI).

This project standardizes challenge directories into platform-compliant container deliverables and validates them during generation. Default outputs are:

- `Dockerfile`
- `start.sh`
- `flag`

## 1. Project Overview and Positioning

`CloverSec-CTF-Build-Dockerizer` is designed to make challenge container delivery repeatable, traceable, and auditable.

Core value:

- Reduce manual orchestration errors and platform incompatibility risks
- Unify config input, template rendering, and rule validation in one workflow
- Support multi-stack challenge delivery under the same standards

## 2. Scope and Out-of-Scope

In scope:

- CTF Jeopardy container delivery
- Stacks: `node` / `php` / `python` / `java` / `tomcat` / `lamp` / `pwn` / `ai`

Out of scope:

- AWD / AWDP competition orchestration
- Production microservice governance (traffic mesh, autoscaling, canary operations)

## 3. One-Command Install

Codex install command:

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

List installable skills in this repository:

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

## 4. Quick Start

### 4.1 AI-Orchestrated Flow (Recommended)

Prompt example:

```text
Please use CloverSec-CTF-Build-Dockerizer for the current challenge directory.
Run auto-detection and output CONFIG PROPOSAL first; after I reply OK, generate Dockerfile/start.sh/flag and run validate.
```

Flow:

1. Detect stack and runtime hints (`derive_config.py`)
2. Generate `CONFIG PROPOSAL`
3. User replies `OK` (or edits YAML)
4. Run `parse_config_block.py -> render.py -> validate.sh`

### 4.2 Manual Command Chain

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-demo:latest .
docker run -d -p 8080:80 ctf-demo:latest /start.sh
```

## 5. Platform Hard Constraints

The following are mandatory before delivery:

1. Containers must start via `/start.sh`
2. `/flag` must exist in image root and be readable
3. `/bin/bash` must be available in the image
4. Dockerfile must include `EXPOSE`
5. Idle keepalive patterns are forbidden (e.g. `sleep infinity`)
6. Single-service entry must run in foreground with `exec`

Details: [platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## 6. Supported Stack Matrix

| Stack | Default Port | Start Example |
|---|---:|---|
| node | 3000 | `exec node server.js` |
| php | 80 | `exec apache2-foreground` |
| python | 5000 | `exec python app.py` / `exec gunicorn ...` |
| java | 8080 | `exec java -jar app.jar` |
| tomcat | 8080 | `exec catalina.sh run` |
| lamp | 80 | DB in background + Apache in foreground |
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` |
| ai | 5000 | `exec gunicorn ...` |

## 7. Repository Structure

```text
.
├── src/CloverSec-CTF-Build-Dockerizer/
│   ├── SKILL.md
│   ├── data/
│   ├── templates/
│   ├── scripts/
│   ├── examples/
│   └── docs/
├── scripts/
│   ├── sync.sh
│   ├── doc_guard.sh
│   ├── release_build.sh
│   └── publish_release.sh
├── CHANGELOG.md
└── VERSION
```

Document entry points:

- Protocol: [SKILL.md](src/CloverSec-CTF-Build-Dockerizer/SKILL.md)
- Beginner guide: [beginner_guide.md](src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md)
- Stack cookbook: [stack_cookbook.md](src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md)
- Troubleshooting: [troubleshooting.md](src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md)

## 8. Release Workflow

### 8.1 Standard Checks and Packaging

```bash
bash scripts/release_build.sh
```

Expected outputs:

- `dist/CloverSec-CTF-Build-Dockerizer-vX.Y.Z/`
- `dist/CloverSec-CTF-Build-Dockerizer-vX.Y.Z.zip`

### 8.2 One-Command Publish (Recommended)

```bash
bash scripts/publish_release.sh --version v1.2.4
```

Sync from a private source repository, then publish:

```bash
bash scripts/publish_release.sh --source-dir /path/to/CloverSec-CTF-Build-Dockerizer --version v1.2.4
```

## 9. Versioning and Changelog

- Current version: `v1.2.4`
- Full history: [CHANGELOG.md](CHANGELOG.md)
- Releases: <https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases>

## 10. Security Boundary and Sensitive Data Policy

- `internal/` is excluded from the public repository
- Do not commit real production secrets or sensitive business data
- Example `flag` files are for workflow verification only
- Always run checks before release to prevent path/privacy leakage

## 11. FAQ

### Q1: Does `npx skills add` depend on release assets?
No. `npx skills add` installs from repository content. Release assets are for versioned download and archival.

### Q2: Why are `/start.sh`, `/flag`, and `/bin/bash` mandatory?
They are platform contract requirements. Missing any of them can break startup or dynamic flag injection.

### Q3: Should documentation-only changes be released?
Yes. Public docs affect external adoption and should remain versioned and traceable.

### Q4: Why keep `internal` out of this repository?
`internal` usually contains private material or sensitive samples and should be archived locally, not published.

## 12. Maintenance and Contribution

Recommended pre-PR checks:

```bash
bash scripts/release_build.sh
npx -y skills add . --list
```

Contribution focus:

- Template and validation rule improvements
- Example and documentation quality
- Release reliability and automation

Maintained by CloverSec R&D Center.

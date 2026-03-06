# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.md"><strong>简体中文（Default）</strong></a>
  <span> · </span>
  <a href="README.en.md"><strong>English</strong></a>
  <span> · </span>
  <a href="README.ja.md"><strong>日本語</strong></a>

</p>

<p align="center">
  <img src="docs/assets/readme/CloverSec-CTF-Build-Dockerizer-skill.svg" alt="CloverSec-CTF-Build-Dockerizer-skill" width="920" />
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v2.0.3--r1-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-11-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/profiles-jeopardy%2Frdg%2Fawd%2Fawdp%2Fsecops-16a34a?style=for-the-badge" alt="Profiles" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v2.0.3-r1"><img src="https://img.shields.io/badge/release-zip%2Bsbom%2Bdeps-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v2.0.3-r1</code></p>

CloverSec-CTF-Build-Dockerizer is a challenge delivery skill from CloverSec R&D Center. Its job is not just "generate Dockerfile", but to turn CTF container delivery into a predictable engineering pipeline.

If you have ever patched `start.sh` minutes before kickoff, or found contract failures after packaging, this README is designed to remove that uncertainty. You can use this page end-to-end: install, proposal confirmation, single challenge rendering, scenario orchestration, local regression, and release publishing.

## v2.0.3 Highlights

### v1.5.0: Governance baseline and runtime compatibility

`v1.5.0` moved the project from "works on my machine" to maintainable release engineering:

- Python-first governance scripts: `doc_guard.py`, `release_build.py`, `generate_sbom.py`, `sync.py`, `publish_guard.py`.
- Runtime profile source `runtime_profiles.yaml`, plus runtime evidence from `derive_config.py`.
- Better alignment between platform contract docs and implementation behavior.

### v2.0.0: Major capability expansion

`v2.0.0` introduced the V2 architecture:

- Primary config model `challenge.profile + challenge.defense`, with legacy `challenge.rdg` compatibility.
- Hard contract upgrade: every render emits `Dockerfile + start.sh + changeflag.sh`.
- New stacks: `stack=secops`, `stack=baseunit`.
- New orchestration entrypoints: `render_component.py`, `render_scenario.py`, `validate_scenario.py`.
- AWDP fixed patch contract: `patch/src/ + patch/patch.sh + patch_bundle.tar.gz`.

### v2.0.1: Closing gaps and reproducibility

`v2.0.1` focused on final-mile robustness:

- Added `scenario-vulhub-like-basic` migration example.
- Removed duplicate stack definitions and made duplicate IDs fail fast.
- AWDP patch bundle switched to deterministic packaging.

### v2.0.3: Chinese default and full documentation expansion

`v2.0.3` is documentation-first, without runtime behavior changes:

- `README.md` is now the full Chinese default manual.
- `README.en.md` and `README.ja.md` are now full equivalent manuals.
- Added AI coding playbooks (Codex, Cursor, Trae, Claude Code, Copilot Chat, Aider).
- Added mode-by-mode build guide (Jeopardy / RDG / AWD / AWDP / SecOps / BaseUnit / Vulhub-like).
- Added file-level directory index, FAQ, troubleshooting, and release checklist.
- Removed external "References" section and kept navigation fully repository-driven.

## Core Capability Matrix

| Capability | Entry Script | Purpose | Output |
|---|---|---|---|
| Auto proposal | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` | Infer stack/ports/start/runtime/profile signals | `config_proposal` |
| Proposal parsing | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | Convert `CONFIG PROPOSAL` into `challenge.yaml` | normalized config |
| Single challenge render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | Generate platform delivery artifacts | `Dockerfile/start.sh/changeflag.sh/(flag optional)` |
| Contract validation | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | Enforce platform constraints and policy checks | `ERROR/WARN/INFO` |
| Component render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | Generate component+variant base units | build-ready service directory |
| Scenario render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | Render local multi-service orchestration | service dirs + `docker-compose.yml` |
| Scenario validation | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | Validate mode/profile/ports/AWDP patch contract | pass/fail |
| Example regression | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | Batch regression for examples and scenarios | summary report |
| Smoke testing | `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` | Build-level fast regression | pass/fail |
| Release packaging | `scripts/release_build.sh` / `scripts/publish_release.sh` | Build assets and publish release | zip/sbom/deps |

## One-Command Install and Discovery

Validate skill discovery first, then install:

```bash
npx -y skills add . --list

npx -y skills add \
  https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill \
  --skill cloversec-ctf-build-dockerizer \
  --agent codex -y
```

After installation, run one full example loop to validate your local Docker and script environment.

### Codex UI Display Strategy

Skill card presentation in Codex UI is controlled by `src/CloverSec-CTF-Build-Dockerizer/agents/openai.yaml`. This file defines:

- `display_name`: the card title shown in the UI
- `short_description`: the subtitle shown under the title
- `brand_color`: the card accent color
- `default_prompt`: the prefilled prompt used for try/run actions
- `allow_implicit_invocation`: whether the model may invoke the skill implicitly when the task matches

The current default prompt strategy is: detect stack and `profile` first, then generate compliant `Dockerfile` / `start.sh` / `changeflag.sh`, and finally run `validate` with delivery guidance. This layer only affects how the skill is presented and started in Codex UI. It does not change the runtime behavior of `render.py`, `validate.sh`, `render_component.py`, or `render_scenario.py`.

If you want to adjust the Codex card title, subtitle, or trial prompt later, edit this file first instead of rewriting the README body:

```yaml
interface:
  display_name: "CloverSec CTF Build Dockerizer"
  short_description: "标准化题目容器交付、BaseUnit 构建与 Scenario 编排"
  default_prompt: "Use $cloversec-ctf-build-dockerizer to处理当前题目目录，先自动探测技术栈与 profile，再生成合规的 Dockerfile/start.sh/changeflag.sh，并执行 validate 与交付建议。"
```

## Quick Start

### Agent-Orchestrated flow (recommended)

Standard prompt template:

```text
Please use CloverSec-CTF-Build-Dockerizer for the current challenge directory.
Run auto-detection first and output CONFIG PROPOSAL with evidence.
After I reply OK, generate Dockerfile/start.sh/changeflag.sh and run validate.
```

Shortcut prompt:

```text
The src folder is my CTF challenge source. Build a platform-compliant container delivery package.
```

### Manual command chain

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### Runtime profile selection (PHP/Node/Java)

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config challenge.yaml \
  --runtime-profile php74-apache \
  --output .
```

Image precedence: `--base-image > --runtime-profile > challenge.base_image > infer/default`.

## AI Coding Playbook

This section is intentionally operational. Each tool includes: call pattern, recommended prompt, retry prompt, acceptance commands.

### Codex

Call pattern: work in repository root and enforce "proposal -> confirm -> render -> validate".

Recommended prompt:

```text
Use CloverSec-CTF-Build-Dockerizer for the current directory.
Run derive_config.py first and output CONFIG PROPOSAL with evidence.
After I confirm, execute render + validate + smoke and report fixes for failures.
Target mode: <jeopardy|rdg|awd|awdp|secops|baseunit|scenario>.
```

Retry prompt:

```text
Do not rerun everything. Apply the minimal fix only for current ERROR items,
then rerun only required checks and report changed files with command results.
```

Acceptance commands:

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
```

### Cursor

Call pattern: ask Cursor to read `challenge.yaml`/`scenario.yaml` before editing.

Recommended prompt:

```text
Use existing repository scripts only; do not replace render.py/validate.sh with handwritten logic.
Output CONFIG PROPOSAL first, then wait for OK before rendering.
Final artifacts must pass Dockerfile/start.sh/changeflag.sh contract checks.
```

Retry prompt:

```text
Keep passing parts unchanged.
Fix only this failure batch and provide copy-paste recheck commands.
```

Acceptance commands:

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### Trae

Call pattern: force four stages: proposal confirmation, render, validation, postmortem.

Recommended prompt:

```text
You are the delivery engineer for this repo.
Stage 1: run derive_config with evidence.
Stage 2: render after my confirmation.
Stage 3: run validate/smoke.
Stage 4: summarize residual risks and release gate checks.
```

Retry prompt:

```text
Split failures into config/template/runtime categories.
Fix one category at a time and revalidate immediately.
```

Acceptance commands:

```bash
npx -y skills add . --list
bash scripts/release_build.sh
```

### Claude Code

Call pattern: ask for an explicit plan + implementation + command summary.

Recommended prompt:

```text
Execute the V2 delivery workflow in this repository:
1) derive_config -> CONFIG PROPOSAL
2) render.py / render_component.py / render_scenario.py (mode dependent)
3) validate.sh / validate_scenario.py / smoke_test.sh
4) summarize failures, fixes, and residual risks
```

Retry prompt:

```text
Ignore completed steps. Focus on the latest failed command.
Explain root cause first, then apply the smallest patch and recheck.
```

Acceptance commands:

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### GitHub Copilot Chat

Call pattern: enforce project-script-only workflow in VS Code chat.

Recommended prompt:

```text
Use repository scripts (derive_config/render/validate) only.
Do not rewrite Dockerfile from scratch.
Show CONFIG PROPOSAL first and wait for confirmation.
```

Retry prompt:

```text
Map each terminal error to exact file/line.
Patch only affected files and rerun impacted checks.
```

Acceptance commands:

```bash
bash scripts/release_build.sh
```

### Aider

Call pattern: run one failing check manually, then let Aider patch targeted files.

Recommended prompt:

```text
Fix this repository based on the following failing logs.
Target checks:
- bash scripts/doc_guard.sh
- bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
Keep architecture unchanged and avoid broad refactors.
```

Retry prompt:

```text
Your patch is too broad. Use a minimal-change strategy:
modify only files directly tied to current failures,
and map each change to one specific error.
```

Acceptance commands:

```bash
git diff --stat
bash scripts/doc_guard.sh
```

## Competition Mode Build Guide

### Jeopardy (Web / Pwn / AI)

Use for standard challenge-solving delivery. Default profile is `jeopardy`.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/node-basic/challenge.yaml \
  --output /tmp/jeopardy-node

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/jeopardy-node/Dockerfile \
  /tmp/jeopardy-node/start.sh \
  /tmp/jeopardy-node/challenge.yaml
```

### RDG

Use for defense + check_service-oriented operations, typically with `stack=rdg`.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/rdg-python-ssti-basic/challenge.yaml \
  --output /tmp/rdg-python

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/rdg-python/Dockerfile \
  /tmp/rdg-python/start.sh \
  /tmp/rdg-python/challenge.yaml
```

### AWD

Use for attack-defense rounds with operator access.

Important: this repo intentionally keeps `stack=awd` out; AWD is implemented as existing stacks plus `profile=awd`.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

### AWDP

Use for attack + fix workflows where teams submit patch bundles instead of live SSH maintenance.

Fixed patch contract:

- `patch/src/`
- `patch/patch.sh`
- `patch_bundle.tar.gz`

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/node-awdp-basic/challenge.yaml \
  --output /tmp/awdp-node

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/awdp-node/Dockerfile \
  /tmp/awdp-node/start.sh \
  /tmp/awdp-node/challenge.yaml
```

### SecOps

Use for security hardening and operation-governance challenges.

Important: `stack=secops + profile=secops` is a dedicated model, not RDG reuse.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/secops-nginx-basic/challenge.yaml \
  --output /tmp/secops-nginx

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/secops-nginx/Dockerfile \
  /tmp/secops-nginx/start.sh \
  /tmp/secops-nginx/challenge.yaml
```

### BaseUnit (versioned service package minimum units)

Use when you need a specific service/version base image without manual dependency compilation.

Initial components: `mysql`, `redis`, `sshd`, `ttyd`, `apache`, `nginx`, `tomcat`, `php-fpm`, `vsftpd`, `weblogic`.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py --list

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --profile jeopardy \
  --output /tmp/baseunit-redis

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/baseunit-redis/Dockerfile \
  /tmp/baseunit-redis/start.sh \
  /tmp/baseunit-redis/challenge.yaml
```

### Vulhub-like migration

Use this when translating a Vulhub-style multi-service lab into this project's boundary:
local compose orchestration + platform single-service delivery.

Boundary rule: generated `docker-compose.yml` is for local orchestration only.
Final platform delivery remains one service directory at a time.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-vulhub-like-basic/scenario.yaml \
  --output /tmp/scenario-vulhub-like

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-vulhub-like
```

## Platform Hard Contract and Boundaries

Every rendered output must satisfy:

- `Dockerfile` exists.
- executable `start.sh` exists.
- executable `changeflag.sh` exists.
- `/bin/bash` exists in container image.
- Dockerfile declares `EXPOSE`.
- `start.sh` launches real service processes (no idle keepalive).

`flag` behavior:

- default: `flag` artifact required.
- if `include_flag_artifact=false`: only `flag` omission is allowed, never `changeflag.sh` omission.

Scenario boundary:

- `docker-compose.yml` is valid for local orchestration/testing.
- platform final delivery is still per-service directory (`Dockerfile + start.sh + changeflag.sh`).

## Workflow Screenshots (prompt to release)

Prompt trigger:

![workflow-01](docs/assets/readme/workflow-01-quick-prompt.png)

Proposal confirmation:

![workflow-02](docs/assets/readme/workflow-02-prebuild-decision.png)

Error closure:

![workflow-03](docs/assets/readme/workflow-03-error-closure.png)

Auto-generated artifacts:

![workflow-04](docs/assets/readme/workflow-04-auto-build.png)

Automated validation:

![workflow-05](docs/assets/readme/workflow-05-auto-validation.png)

Hard contract checks:

![workflow-06](docs/assets/readme/workflow-06-hard-check.png)

Delivery checklist:

![workflow-07](docs/assets/readme/workflow-07-delivery-checklist.png)

## Build_test Real Examples

`Build_test/` stores real challenge cases for reproducible build + validation.

| Case directory | Stack | Port | Start command | Core files |
|---|---|---:|---|---|
| `Build_test/CTF-NodeJs RCE-Test1` | node | 3000 | `node app.js` | `challenge.yaml` `Dockerfile` `start.sh` `app.js` |
| `Build_test/CTF-Python沙箱逃逸-Test2` | python | 5000 | `python app.py` | `challenge.yaml` `Dockerfile` `start.sh` `Build_test/CTF-Python沙箱逃逸-Test2/src/app.py` |

Revalidation commands:

```bash
cd "Build_test/CTF-NodeJs RCE-Test1"
npm ci
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## File-Level Directory Index

### Repository root

| File/Directory | Purpose |
|---|---|
| `README.md` | Full Chinese manual (default entry) |
| `README.en.md` | Full English manual |
| `README.ja.md` | Full Japanese manual |
| `VERSION` | Current release version |
| `CHANGELOG.md` | Version history |
| `LICENSE` | Open-source license |
| `Build_test/` | Real challenge regression cases |
| `dist/` | Release assets from `release_build` |

### `scripts/` (repo-level governance and release)

| File | Purpose |
|---|---|
| `scripts/doc_guard.py` | Primary documentation gate |
| `scripts/doc_guard.sh` | Shell entry for doc guard |
| `scripts/release_build.py` | Primary release packaging implementation |
| `scripts/release_build.sh` | Shell entry for release packaging |
| `scripts/publish_guard.py` | Version + whitelist guard before publish |
| `scripts/publish_release.sh` | commit + push + tag + release orchestration |
| `scripts/generate_sbom.py` | SBOM generation core |
| `scripts/generate_sbom.sh` | SBOM entry |
| `scripts/sync.py` | source-to-publish repo sync logic |
| `scripts/sync.sh` | sync entry |

### `src/CloverSec-CTF-Build-Dockerizer/data`

| File | Purpose |
|---|---|
| `schema.md` | `challenge.yaml` contract |
| `scenario_schema.md` | `scenario.yaml` contract |
| `stacks.yaml` | stack defaults and template mapping |
| `profiles.yaml` | profile default behaviors |
| `components.yaml` | BaseUnit component + variant catalog |
| `runtime_profiles.yaml` | runtime profile definitions |
| `patterns.yaml` | auto-detection patterns |
| `validate_rules.yaml` | rules for `validate.sh` |
| `validate_scenario_rules.yaml` | rules for `validate_scenario.py` |
| `base_image_allowlist.yaml` | allowed base image policy |
| `README.md` | data directory guide |

### `src/CloverSec-CTF-Build-Dockerizer/scripts`

| File | Purpose |
|---|---|
| `derive_config.py` | infer challenge config proposal |
| `parse_config_block.py` | parse `CONFIG PROPOSAL` block |
| `render.py` | single challenge rendering |
| `render_component.py` | BaseUnit rendering |
| `render_scenario.py` | scenario rendering |
| `validate.sh` | single challenge validation |
| `validate_scenario.py` | scenario validation |
| `validate_examples.sh` | batch example regression |
| `smoke_test.sh` | smoke regression |
| `validate_context.py` | challenge context parser helper |
| `autofix.py` | common issue auto-fix helper |
| `detect_stack.py` | stack detection helper |
| `utils.py` | shared utilities |
| `cleanup_test_containers.sh` | test container cleanup |
| `test_runtime_profiles.sh` | runtime profile regression |
| `README.md` | scripts directory guide |

### `src/CloverSec-CTF-Build-Dockerizer/templates`

| Path | Purpose |
|---|---|
| `templates/node|php|python|java|tomcat|lamp|pwn|ai/` | Jeopardy stack templates |
| `templates/rdg/` | RDG dedicated templates |
| `templates/secops/` | SecOps dedicated templates |
| `templates/baseunit/` | BaseUnit common templates |
| `templates/snippets/` | defense/check/changeflag snippets |
| `templates/README.md` | template directory guide |

### `src/CloverSec-CTF-Build-Dockerizer/examples`

| Path | Purpose |
|---|---|
| `examples/*-basic` | minimal single-challenge examples |
| `examples/node-awdp-basic` | AWDP single challenge patch contract example |
| `examples/secops-*-basic` | SecOps examples |
| `examples/baseunit-*` | BaseUnit examples |
| `examples/scenario-awd-basic` | AWD scenario example |
| `examples/scenario-awdp-basic` | AWDP scenario example |
| `examples/scenario-vulhub-like-basic` | Vulhub-like migration example |
| `examples/README.md` | examples guide |

### `src/CloverSec-CTF-Build-Dockerizer/docs`

| File | Purpose |
|---|---|
| `architecture_overview.md` | architecture overview |
| `platform_contract.md` | platform contract |
| `stack_cookbook.md` | stack-specific cookbook |
| `directory_guide.md` | repository structure design |
| `troubleshooting.md` | troubleshooting playbook |
| `beginner_guide.md` | beginner onboarding guide |

## FAQ and Troubleshooting

### Q1: Why are `/start.sh`, `/changeflag.sh`, and `/bin/bash` mandatory?

They are platform runtime contract requirements. Missing any of them can break startup or challenge reset behavior.

### Q2: Why do I still get an error with `include_flag_artifact=false`?

That option only relaxes `flag` artifact requirement. It does not relax `changeflag.sh` requirement.

### Q3: AWD and SecOps look similar. How should I choose?

- Attack-defense operation scenario: existing stack + `profile=awd`.
- Security hardening operation scenario: `stack=secops + profile=secops`.

### Q4: Why does AWDP use patch bundles instead of direct SSH fixing?

AWDP is designed for auditable patch submission workflows. Teams submit `patch/src + patch.sh + tar.gz`; platform applies them automatically.

### Q5: Why can’t I deliver the scenario `docker-compose.yml` directly to platform?

Because target platform accepts single-service delivery directories. Compose is for local orchestration only.

### Q6: Is `npx -y skills add . --list` tied to Release assets?

No. It validates skill discovery. Release assets are packaging/distribution artifacts.

## Maintenance, Contribution, and Release

Minimum pre-release checks:

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh
```

Formal release command:

```bash
bash scripts/publish_release.sh --version v2.0.3-r1
```

If remote tag/release conflicts or authentication failures occur, stop and fix the blocker first. Do not bypass by changing version strategy on the fly.

## License

This project is licensed under the [MIT License](LICENSE).

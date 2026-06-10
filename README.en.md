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
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v2.2.0-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-12-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/profiles-jeopardy%2Frdg%2Fawd%2Fawdp%2Fsecops-16a34a?style=for-the-badge" alt="Profiles" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v2.2.0"><img src="https://img.shields.io/badge/release-zip%2Bsbom%2Bdeps-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v2.2.0</code></p>

CloverSec-CTF-Build-Dockerizer is a challenge delivery skill from CloverSec R&D Center. Its job is not just "generate Dockerfile", but to turn CTF container delivery into a predictable engineering pipeline.

If you have ever patched `start.sh` minutes before kickoff, or found contract failures after packaging, this README is designed to remove that uncertainty. You can use this page end-to-end: install, proposal confirmation, single challenge rendering, scenario orchestration, local regression, and release publishing.

## v2.2.0 Major Updates

`v2.2.0` is a focused upgrade based on months of real usage and Agent workflow issues. It targets common delivery problems in real competition work: dirty challenge directories, mixed input sources, legacy projects with compose or Vulhub-like structures, and Linux kernel CVE / LPE challenges that cannot be faithfully reproduced in ordinary Docker because containers share the host kernel. This release also reduces the Skill entry size and improves context management, so the same task loads less context, starts faster, and consumes fewer tokens.

This release covers:

1. Broader real competition coverage: Jeopardy, Web, Pwn, AI, RDG, AWD, AWDP, SecOps, BaseUnit, Scenario/Vulhub-like, Bundle/Recipe, and Linux-QEMU. Platform delivery still uses the single-service `Dockerfile + start.sh + changeflag.sh` format, while multi-service orchestration is mainly for local validation, migration, and organizing complex challenges.
2. Dedicated Linux kernel CVE / LPE delivery: the platform still sees one Docker artifact, but the container starts an independent Linux guest environment through QEMU to carry the target kernel, rootfs, and challenge service. This keeps the platform delivery shape while giving kernel challenges a runtime closer to the real vulnerable environment.
3. Proposal confirmation for complex input: mixed input, dirty directories, high-risk input, compose/Vulhub-like projects, missing Linux-QEMU assets, and cPanel/WHM-like inputs enter proposal confirmation. Manual continuation records the reason in text or JSON output.
4. Example validation closer to real projects: `validate_examples.sh` is read-only by default, `Build_test/` supports expected pass and expected fail cases, Scenario validates each rendered service, and Linux-QEMU provides validation levels from preflight to full checks.
5. Bundle, Compose, and check-service expansion: v2.2.0 adds Bundle Recipe prototypes, compose/Vulhub-like import drafts, and HTTP/TCP/Redis/MySQL/SSH check-service stubs.
6. Clearer pre-release status: rendering, scenario validation, and release checks support structured output.
7. Lighter Skill entry through progressive disclosure: `SKILL.md` dropped from 1089 to 206 lines, a reduction of about 81.1%; bytes dropped from 39254 to 10204, a reduction of about 74.0%. The same task now requires less entry context and loads faster.

## Core Capability Matrix

| Capability | Entry Script | Purpose | Output |
|---|---|---|---|
| Stateful workflow | `src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py` | Orchestrate analysis, confirmation, rendering, validation, and status tracking | `.ctfbuild/session.json` |
| Input audit and proposal | `src/CloverSec-CTF-Build-Dockerizer/scripts/audit_input.py` / `derive_config.py` | Infer stack, ports, start command, runtime, profile, and risk level | audit result / build plan |
| Build-plan parsing | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | Convert the confirmed plan into `challenge.yaml` | normalized config |
| Single challenge render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | Generate platform delivery artifacts | `Dockerfile/start.sh/changeflag.sh/(flag optional)` |
| Contract validation | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | Enforce platform constraints and policy checks | `ERROR/WARN/INFO` / JSON summary |
| Component render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | Generate component+variant base units | build-ready service directory |
| Bundle/Recipe render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_bundle.py` / `validate_bundle.py` | Generate and validate fixed single-container multi-service recipes | platform delivery directory |
| Compose/Vulhub-like import | `src/CloverSec-CTF-Build-Dockerizer/scripts/import_compose.py` | Produce draft, renderable subset, and import report | `scenario.draft.yaml` / `scenario.renderable.yaml` / `import-report.json` |
| Check-service stub | `src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py` | Generate HTTP/TCP/Redis/MySQL/SSH check skeletons | review-required `check/check.sh` |
| Linux-QEMU render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | Generate Docker-hosted QEMU guest delivery | single-image delivery directory |
| Linux-QEMU manual validation | `scripts/linux_qemu_manual_check.sh` | Run preflight/static/build/boot/flag/full checks | JSON summary / evidence notes |
| Scenario render | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | Render local multi-service orchestration | service dirs + `docker-compose.yml` |
| Scenario validation | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | Validate mode/profile/ports/AWDP patch contract | pass/fail |
| Example regression | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | Batch regression for examples and scenarios | summary report |
| Smoke testing | `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` | Build-level fast regression | pass/fail |
| Real sample pool regression | `scripts/validate_build_test.py` | Validate Build_test cases against expected pass/fail outcomes | structured summary |
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

The current default prompt strategy is: inspect the challenge directory first, summarize evidence, risks, and missing information, then ask the user to confirm the build plan. After confirmation, the skill generates the Docker delivery files and runs validation. This layer only affects how the skill is presented and started in Codex UI. It does not change the runtime behavior of `workflow.py`, `render.py`, `validate.sh`, `render_component.py`, or `render_scenario.py`.

If you want to adjust the Codex card title, subtitle, or trial prompt later, edit this file first instead of rewriting the README body:

```yaml
interface:
  display_name: "CloverSec CTF Build Dockerizer"
  short_description: "将 CTF 题目整理为可验证的 Docker 交付件，支持内核题与多服务场景"
  default_prompt: "<Chinese prompt stored in agents/openai.yaml>"
```

## Quick Start

### AI-assisted flow (recommended)

Standard prompt template:

```text
Please use CloverSec-CTF-Build-Dockerizer for the current challenge directory.
Inspect the challenge structure, risks, and missing information first.
After I confirm the build plan, generate the Docker delivery files and run validation.
```

Shortcut prompt:

```text
The src folder is my CTF challenge source. Build a platform-compliant container delivery package.
```

### Manual command chain

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py intake --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py propose --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py accept --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py render --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py validate --project-dir .
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
Inspect the challenge structure, risks, and missing information first.
After I confirm the build plan, generate the delivery files and run the relevant validation command.
Target mode: <jeopardy|rdg|awd|awdp|secops|baseunit|scenario|bundle|linux-qemu|compose-import>.
```

Retry prompt:

```text
Do not rerun everything. Fix only the current ERROR items,
then rerun the required checks and report changed files with command results.
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
Use existing repository scripts only; do not replace workflow.py/render.py/validate.sh with handwritten logic.
Inspect the challenge first, then wait for confirmation before rendering.
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

Call pattern: force four stages: build-plan confirmation, render, validation, postmortem.

Recommended prompt:

```text
You are the delivery engineer for this repo.
Stage 1: inspect the challenge and present the build plan with evidence.
Stage 2: after my confirmation, generate the delivery files.
Stage 3: run validate / validate_scenario / validate_bundle / smoke as applicable.
Stage 4: summarize release gate checks and manual verification items.
```

Retry prompt:

```text
Split failures into config/template/runtime categories.
Fix one category at a time and revalidate immediately.
```

Acceptance commands:

```bash
npx -y skills add . --list
bash scripts/release_build.sh --with-smoke
```

### Claude Code

Call pattern: ask for an explicit plan + implementation + command summary.

Recommended prompt:

```text
Execute the V2 delivery workflow in this repository:
1) inspect the challenge and produce a build plan with evidence
2) generate the delivery files or use a mode-specific renderer when required
3) validate.sh / validate_scenario.py --validate-rendered / validate_bundle.py / smoke_test.sh
4) summarize failures, fixes, and manual verification items
```

Retry prompt:

```text
Ignore completed steps. Focus on the latest failed command.
Explain the failure first, then patch the affected files and recheck.
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
Use repository scripts (workflow/render/validate/import_compose/render_bundle) only.
Do not rewrite Dockerfile from scratch.
Show the build plan with input evidence first and wait for confirmation.
```

Retry prompt:

```text
Map each terminal error to exact file/line.
Patch only affected files and rerun impacted checks.
```

Acceptance commands:

```bash
bash scripts/release_build.sh --with-smoke
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

### Linux-QEMU (Linux kernel CVE / LPE)

Use when the challenge needs a specific guest kernel, initrd/rootfs, kernel module, or kernel configuration. The platform still receives one Docker image; `/start.sh` runs QEMU inside the container, and the vulnerable environment runs in the guest.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/linux-qemu-basic/challenge.yaml \
  --output /tmp/linux-qemu-basic

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/linux-qemu-basic/Dockerfile \
  /tmp/linux-qemu-basic/start.sh \
  /tmp/linux-qemu-basic/challenge.yaml
```

Delivery notes:

- `guest_forwards[*].proto` is TCP-only in the current release.
- The default smoke path renders and validates the placeholder sample; full QEMU boot and exploit replay require real VM assets.
- `flag_injection=debugfs` requires `changeflag.sh` to write the guest flag path into the rootfs image.

Manual validation entrypoints:

```bash
bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir /path/to/linux-qemu/code
bash scripts/linux_qemu_manual_check.sh --mode boot --case-dir /path/to/linux-qemu/code --host-port 2222
```

See `src/CloverSec-CTF-Build-Dockerizer/docs/linux_qemu_manual_validation.md` for validation levels, TCG/KVM boundaries, dynamic flag injection, and PoC evidence notes.

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

Use `generate_check_stub.py` to generate editable HTTP/TCP/Redis/MySQL/SSH check-service skeletons:

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py \
  --type http \
  --output /tmp/rdg-python/check/check.sh \
  --target-port 8080 \
  --path /
```

Generated scripts contain `CHECK_REVIEW_REQUIRED`; remove it only after reviewing the actual check logic.

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

The command above validates scenario/compose structure only. Add `--validate-rendered` when each rendered service directory should also pass `validate.sh`.

Batch regression entrypoints `validate_examples.sh` and `smoke_test.sh` enable rendered-service validation for scenario examples by default. Set `SCENARIO_VALIDATE_RENDERED=0` when you only want the lightweight scenario/compose structure check.

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

### Bundle / Recipe

Use for a small fixed matrix of legacy single-container multi-service environments. BaseUnit is a single component, Scenario is local multi-service orchestration, and Bundle is a limited Recipe inside one Docker image.

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_bundle.py \
  --recipe legacy-centos7-python39-mysql57-redis5 \
  --output /tmp/bundle

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_bundle.py \
  --bundle-dir /tmp/bundle

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/bundle/Dockerfile \
  /tmp/bundle/start.sh \
  /tmp/bundle/challenge.yaml
```

Unsupported combinations return `BUNDLE_UNSUPPORTED_COMBINATION`; they are not silently rewritten as another stack.

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

The command above validates scenario/compose structure only. Add `--validate-rendered` when each rendered service directory should also pass `validate.sh`. Batch regression enables rendered-service validation by default; set `SCENARIO_VALIDATE_RENDERED=0` to keep structure-only validation.

For existing compose input, generate a draft, a renderable subset, and an import report first:

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/import_compose.py \
  --compose docker-compose.yml \
  --scenario-name imported-lab \
  --output /tmp/imported-lab
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
| `scripts/validate_build_test.py` | Build_test real sample pool regression |
| `scripts/linux_qemu_manual_check.sh` | Linux-QEMU release/manual validation |
| `scripts/generate_sbom.py` | SBOM generation core |
| `scripts/generate_sbom.sh` | SBOM entry |
| `scripts/sync.py` | source-to-publish repo sync logic |
| `scripts/sync.sh` | sync entry |

### `src/CloverSec-CTF-Build-Dockerizer/data`

| File | Purpose |
|---|---|
| `schema.md` | `challenge.yaml` contract |
| `scenario_schema.md` | `scenario.yaml` contract |
| `bundle_schema.md` / `bundle_recipes.yaml` | Bundle/Recipe contract and fixed recipe definitions |
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
| `audit_input.py` | input risk audit |
| `workflow.py` | stateful analysis, confirmation, rendering, validation, and status orchestration |
| `parse_config_block.py` | parse the confirmed build-plan block |
| `render.py` | single challenge rendering |
| `render_component.py` | BaseUnit rendering |
| `render_bundle.py` / `validate_bundle.py` | Bundle/Recipe rendering and validation |
| `import_compose.py` | compose/Vulhub-like import draft |
| `generate_check_stub.py` | RDG/SecOps check-service skeleton generation |
| `render_scenario.py` | scenario rendering |
| `validate.sh` | single challenge validation |
| `validate_scenario.py` | scenario validation |
| `validate_examples.sh` | batch example regression |
| `smoke_test.sh` | smoke regression |
| `validate_context.py` | challenge context parser helper |
| `autofix.py` | common issue auto-fix helper |
| `detect_stack.py` | stack detection helper |
| `result_utils.py` | structured result output helper |
| `utils.py` | shared utilities |
| `requirements.txt` | Python script dependencies |
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
| `templates/linux-qemu/` | QEMU guest template for Linux kernel CVE/LPE challenges |
| `templates/snippets/` | defense/check/changeflag snippets |
| `templates/README.md` | template directory guide |

### `src/CloverSec-CTF-Build-Dockerizer/examples`

| Path | Purpose |
|---|---|
| `examples/*-basic` | minimal single-challenge examples |
| `examples/node-awdp-basic` | AWDP single challenge patch contract example |
| `examples/secops-*-basic` | SecOps examples |
| `examples/baseunit-*` | BaseUnit examples |
| `examples/bundle-*` | Bundle/Recipe examples |
| `examples/linux-qemu-basic` | Linux-QEMU sample with placeholder VM assets |
| `examples/scenario-awd-basic` | AWD scenario example |
| `examples/scenario-awdp-basic` | AWDP scenario example |
| `examples/scenario-vulhub-like-basic` | Vulhub-like migration example |
| `examples/scenario-compose-import-basic` | compose import draft example |
| `examples/README.md` | examples guide |

### `src/CloverSec-CTF-Build-Dockerizer/docs`

| File | Purpose |
|---|---|
| `architecture_overview.md` | architecture overview |
| `platform_contract.md` | platform contract |
| `orchestrated_workflow.md` | build-plan confirmation, OK gate, and five confirmation items |
| `stack_cookbook.md` | stack-specific cookbook |
| `validation_guide.md` | validation rules, check-service gate, and release checks |
| `directory_guide.md` | repository structure design |
| `linux_qemu_manual_validation.md` | Linux-QEMU manual/release validation guide |
| `bundle_design.md` | Bundle/Recipe design boundary |
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
bash scripts/release_build.sh --with-smoke
```

Formal release command:

```bash
bash scripts/publish_release.sh --version v2.2.0
```

If remote tag/release conflicts or authentication failures occur, stop and fix the blocker first. Do not bypass by changing version strategy on the fly.

## License

This project is licensed under the [MIT License](LICENSE).

<p align="center">
  <img src=".github/assets/banner.svg" alt="CloverSec CTF Pack" width="860" />
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Pack/releases/latest"><img src="https://img.shields.io/github/v/release/D1a0y1bb/CloverSec-CTF-Pack?style=for-the-badge&color=2563eb&label=release" alt="Release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/D1a0y1bb/CloverSec-CTF-Pack?style=for-the-badge&color=16a34a" alt="License" /></a>
  <img src="https://img.shields.io/badge/Claude_Code_%C2%B7_Codex-skill-f59e0b?style=for-the-badge" alt="Claude Code · Codex" />
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#output">Output</a> ·
  <a href="#manual">Manual</a> ·
  <a href="#local-verification">Local verification</a> ·
  <a href="#flag-contract">Flag contract</a> ·
  <a href="#layout">Layout</a>
</p>

---

An agent skill used by the CloverSec R&D Center to package CTF challenges. Give Claude Code or Codex the challenge source, a design note, or an old challenge directory. For container challenges it produces a buildable directory and verifies it locally; for attachment challenges it organises the player-facing files. Both get a manual.

- Directories are named `<type>-<name>`, where type is one of 20 categories such as Web, Pwn, Crypto or AI.
- The source, `Dockerfile` and `start.sh` are written from the examples in the skill, with comments that point out the vulnerability and any non-obvious configuration. Comments are in Chinese.
- `verify.sh` runs a container challenge the way the platform does: amd64 build, start with `/start.sh`, write a random test flag, probe the ports, and run `solve/solve.py` when present, which must print that flag.
- The manual lives in `README/`; `solve/`, `附件/` (attachments) and `镜像/` (image tarball) sit next to `src/`.
- For challenges that must stay buildable for years, the references show how to pin image digests, apt snapshots and dependency versions.
- Multi-service, Bundle, Scenario, RDG/AWD and Linux-QEMU challenges have their own reference file. Regular challenges never load it.

## Install

```bash
npx skills add D1a0y1bb/CloverSec-CTF-Pack -g -a claude-code -a codex
```

`-g` installs into `~/.agents/skills/`, and Claude Code reads it through a symlink. Drop `-g` to install into the current project. Pass `-a` once per agent.

Verification needs Docker and `curl`. On Apple Silicon the amd64 build runs under emulation and is slower.

## Usage

Name the skill in the chat, then hand over the material. Claude Code uses `/cloversec-ctf-pack`, Codex uses `$cloversec-ctf-pack`:

```text
/cloversec-ctf-pack Turn ./ssti-notes into a platform challenge.
Flask SSTI, flag at /flag, port 5000.
```

The material can be a design note, a bare source tree, or an old challenge with its own Dockerfile. If something that blocks the build is missing (port, start command, runtime version, flag path), it asks for all of it in one go instead of guessing.

## Output

A container challenge:

```text
Web-afterimage/
├── README/
│   ├── Web-afterimage.md   # manual
│   └── assets/             # screenshots used by the manual
├── src/
├── Dockerfile
├── start.sh                # platform entrypoint, runs the real service in the foreground
├── challenge.yaml          # port, flag path and other platform fields
├── flag                    # placeholder, overwritten by the platform at start
├── solve/
│   └── solve.py            # local verification only, never copied into the image
└── 附件/                    # player attachments, only when the challenge needs them
```

An attachment-only challenge has no image files: just `README/`, `src/`, `附件/` and `solve/`. `镜像/` is created only when an image tarball is requested.

## Manual

The manual is part of the deliverable, written to `README/<type>-<name>.md`, with screenshots in `README/assets/`. The section order is fixed: name, description, difficulty, what it tests, flag, challenge details, deployment, design, solution steps. See [references/manual.md](src/CloverSec-CTF-Pack/references/manual.md) for the skeleton.

## Local verification

```bash
bash ~/.agents/skills/cloversec-ctf-pack/scripts/verify.sh ./ssti-notes
```

The script builds for `linux/amd64`, starts the container with `/start.sh`, waits until the ports are really listening, writes a random test flag to `flag.path`, then probes the ports. If `solve/solve.py` exists it runs it (target address in `HOST` and `PORT`) and only passes if the output contains that test flag, which catches services that cache the flag at startup. Use `--solve '<command>'` for solvers in other languages. The container and image are removed afterwards; pass `--keep` to leave them.

```text
== 构建镜像 (linux/amd64)
   完成，用时 16 秒
== 启动容器
   等待端口 5000 开始监听（最多 60 秒）
   容器运行中
== 写入测试 Flag 到 /flag
   回读一致（444 root:root）
== 探测端口 5000（本机 127.0.0.1:61197）
   HTTP 200
== 运行解题命令: python3 solve/solve.py
   拿到测试 Flag

== 结果: passed
```

| Result | Exit code | Meaning |
|---|---|---|
| `passed` | 0 | Every check passed |
| `partial` | 3 | It runs, but some checks were skipped (e.g. no port declared); each one is listed |
| `failed` | 1 | Build failed, container exited, port bound to 127.0.0.1 only, flag not writable, or the solve script did not get the flag |

Port and flag path come from `challenge.yaml` by default. Override them with `--port` and `--flag-path`. See `verify.sh --help` for all options.

## Flag contract

Once the container is up, the platform writes the round's dynamic flag into the file named by `flag.path` in `challenge.yaml`. That has to be the file the program actually reads:

| Category | Usual path |
|---|---|
| Web / AI / Misc | `/flag` |
| Pwn | `/home/ctf/flag` (`root:ctf`, `440`) |
| Flag embedded in PHP | `/var/www/html/flag.php` |
| Database | Document the SQL that updates the flag |

Read the flag file on every request. If it is read once at startup and cached (a Python module-level variable, a Java `static` block), the platform's new flag never shows up.

## Layout

```text
src/CloverSec-CTF-Pack/
├── SKILL.md              # entry: output layout, workflow, examples, comment rules, flag contract
├── agents/openai.yaml    # name and default prompt shown in Codex
├── references/
│   ├── platform.md       # how the platform starts challenges, env-var flags, image tar formats, challenge.yaml
│   ├── dockerfiles.md    # Dockerfile / start.sh per language, Pwn, version pinning
│   └── special.md        # multi-service, Bundle, Scenario, RDG/AWD, Linux-QEMU
└── scripts/
    └── verify.sh         # local build and run check
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE)

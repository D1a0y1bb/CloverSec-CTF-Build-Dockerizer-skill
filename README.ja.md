# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span> · </span>
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
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

CloverSec-CTF-Build-Dockerizer は、CTF 問題環境の Docker 配布を標準化するためのビルド/検証エンジンです。Jeopardy、RDG、AWD/AWDP 互換プロファイル、SecOps、BaseUnit、Scenario ローカル編成を 1 つのワークフローで扱います。

## v2.0.0 の主な更新

- プラットフォーム契約を強化し、毎回 `Dockerfile + start.sh + changeflag.sh` を生成。
- V2 設定モデルを導入：`challenge.profile` と `challenge.defense` を主入力化（`challenge.rdg` は互換入力として維持）。
- 独立スタックを追加：`stack=secops`、`stack=baseunit`。
- コンポーネント最小ユニット生成を追加：
  - `data/components.yaml`
  - `scripts/render_component.py`
- シナリオ編成パイプラインを追加：
  - `scripts/render_scenario.py`
  - `scripts/validate_scenario.py`
  - `data/scenario_schema.md`
- AWDP 固定パッチ契約を追加：
  - `patch/src/`
  - `patch/patch.sh`
  - `patch_bundle.tar.gz`
- 英語/中国語/日本語の完全ドキュメントを提供。

## 機能マトリクス

| 機能 | エントリ | 目的 | 出力 |
|---|---|---|---|
| 自動提案 | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` | スタック/ポート/起動コマンド/profile を推定 | `config_proposal` |
| 提案パース | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | `CONFIG PROPOSAL` を `challenge.yaml` に変換 | 正規化設定 |
| 単体レンダ | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | 単一問題の配布物を生成 | `Dockerfile/start.sh/changeflag.sh/(flag optional)` |
| BaseUnit 生成 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | component + variant を最小ユニット化 | そのまま build 可能 |
| シナリオ生成 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | 複数サービスのローカル編成を生成 | service dir + `docker-compose.yml` |
| シナリオ検証 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | mode/profile/port/AWDP 契約を検証 | pass/fail |
| 契約検証 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | ハードルールとポリシー検査 | ERROR/WARN/INFO |
| サンプル回帰 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | examples 全体の回帰実行 | 集計結果 |

## クイックスタート

### 1) 単一問題をレンダリング

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### 2) BaseUnit コンポーネントを生成

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --output /tmp/baseunit-redis
```

### 3) AWD/AWDP シナリオをローカル生成

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

## プラットフォーム契約（V2）

各レンダ結果は以下を満たす必要があります。

- `/start.sh` が存在し実行可能
- `/changeflag.sh` が存在し実行可能
- イメージ内に `/bin/bash` が存在
- Dockerfile に `EXPOSE` がある
- `start.sh` は実サービスを起動（空回し keepalive 禁止）

`/flag` の扱い:

- デフォルトでは必須
- 防御プロファイルで `include_flag_artifact=false` を明示した場合のみ省略可（主に RDG/AWDP/SecOps の check-service 型）

## V2 profile / defense

サポート profile:

- `jeopardy`
- `rdg`
- `awd`
- `awdp`
- `secops`

優先順位:

- 主入力: `challenge.defense`
- 互換入力: `challenge.rdg`
- 内部で 1 つの防御モデルへ正規化

## BaseUnit 初期 10 コンポーネント

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

バリアント一覧は `render_component.py --list` で確認できます。

## AWD/AWDP/Vulhub-like 境界

Scenario が生成する `docker-compose.yml` はローカル検証用です。プラットフォーム最終納品は引き続き単一サービス形式です。

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

### Vulhub-like 移行手順

Vulhub のような複数サービス構成を移行する場合は、次の順で進めます。

1. 各サービスを単一 challenge ディレクトリまたは `baseunit` 変種に分解する
2. `scenario.yaml` にサービス関係とポートを記述する
3. `render_scenario.py` + `validate_scenario.py` でローカル検証する
4. 生成された各サービスを単体納品としてプラットフォームへ投入する

## AWDP パッチワークフロー

`profile=awdp` のサービスでは以下が必須です。

- `patch/src/`
- 実行可能 `patch/patch.sh`
- 2 つを含む `patch_bundle.tar.gz`

## SecOps と AWD の違い

| 観点 | AWD | SecOps |
|---|---|---|
| 目的 | 攻防 + 可用性維持 | 設定強化と運用ガバナンス |
| 主構成 | web/pwn + `profile=awd` | `stack=secops` + `profile=secops` |
| ログイン運用 | 通常有効 | 方針に応じて制御 |
| 判定 | サービス/攻防プラットフォーム依存 | check-service + hardening 検査 |

## 検証とリリース

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh
bash scripts/publish_release.sh --version v2.0.0
```

## ドキュメント索引

- Skill 仕様: `src/CloverSec-CTF-Build-Dockerizer/SKILL.md`
- 入力 schema: `src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- プラットフォーム契約: `src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- アーキテクチャ: `src/CloverSec-CTF-Build-Dockerizer/docs/architecture_overview.md`
- スタック手引き: `src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- シナリオ schema: `src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md`

## 参考

- [Vulhub](https://github.com/vulhub/vulhub)
- [Quick Start CTF mode docs](https://quickstart-ctf.github.io/quickstart/mode.html)
- [AWDP patch workflow reference (CN)](https://www.cn-sec.com/archives/1948396.html)

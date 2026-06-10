# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.md"><strong>简体中文（デフォルト）</strong></a>
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

CloverSec-CTF-Build-Dockerizer は、CloverSec 研究開発センターの CTF 問題コンテナ配布 Skill です。目的は「Dockerfile を作ること」ではなく、CTF 配布作業を再現可能なエンジニアリングフローへ標準化することです。

大会直前に `start.sh` を場当たり修正したり、パッケージ後に契約違反が見つかった経験があるなら、この README をそのまま運用手順として使えます。インストール、提案確認、単一問題レンダリング、シナリオ編成、回帰検証、リリース公開まで一連で実行できます。

## v2.2.0 主な更新

`v2.2.0` は、数か月にわたる実運用上の問題と Agent ワークフローの改善をまとめた集中アップグレードです。実際の競技問題配布でよく出る、問題ディレクトリが整理されていない、入力ソースが混在している、古いプロジェクトが compose / Vulhub-like 構造を持っている、Linux kernel CVE / LPE 問題を通常の Docker だけでは正しく再現できない、といった課題を重点的に扱います。Skill 入口と context 管理も大きく見直し、同じタスクで読む文脈を減らし、読み込みを速くし、token 消費を抑えます。

この版の内容：

1. 実競技シーンの対応範囲を拡大：Jeopardy、Web、Pwn、AI、RDG、AWD、AWDP、SecOps、BaseUnit、Scenario/Vulhub-like、Bundle/Recipe、Linux-QEMU を対象化。競技プラットフォーム向けの最終成果物は単一サービスの `Dockerfile + start.sh + changeflag.sh` 形式を維持し、複数サービス編成は主にローカル検証、移行、複雑な問題整理に使います。
2. Linux kernel CVE / LPE 専用の配布方式：プラットフォームから見ると 1 つの Docker 成果物ですが、コンテナ内部で QEMU による独立 Linux guest 環境を起動し、指定 kernel、rootfs、問題サービスを載せます。これにより Docker の配布形式を維持しながら、kernel 問題を実際の脆弱環境に近い形で動かせます。
3. 複雑な入力は先に proposal confirmation：mixed input、dirty directory、high-risk input、compose/Vulhub-like project、Linux-QEMU missing assets、cPanel/WHM 系入力は proposal confirmation に入ります。人工確認で進める場合は理由を記録し、text / JSON output に残します。
4. 実プロジェクトに近いサンプル検証：`validate_examples.sh` は既定で read-only、`Build_test/` は expected pass / expected fail を扱える実例プール、Scenario は service ごとの検証、Linux-QEMU は preflight から full validation まで段階的に使えます。
5. Bundle、Compose、service check の拡張：v2.2.0 では Bundle Recipe prototype、compose/Vulhub-like import draft、HTTP/TCP/Redis/MySQL/SSH check-service skeleton を追加しました。
6. リリース前状態を把握しやすく：render、scenario validation、release checks が structured output に対応しました。
7. Progressive disclosure による軽い Skill 入口：`SKILL.md` は 1089 行から 206 行へ減り、約 81.1% 削減。bytes は 39254 から 10204 へ減り、約 74.0% 削減。同じタスクで読む入口文脈を減らし、読み込みを速くしました。

## コア機能マトリクス

| 機能 | エントリスクリプト | 目的 | 出力 |
|---|---|---|---|
| 状態付きワークフロー | `src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py` | intake/propose/accept/render/validate/status を編成 | `.ctfbuild/session.json` |
| 入力監査と提案 | `src/CloverSec-CTF-Build-Dockerizer/scripts/audit_input.py` / `derive_config.py` | スタック/ポート/起動/runtime/profile とリスクを推定 | `input_audit` / `config_proposal` |
| 提案解析 | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | `CONFIG PROPOSAL` を `challenge.yaml` 化 | 正規化設定 |
| 単体レンダリング | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | 単一問題の配布物生成 | `Dockerfile/start.sh/changeflag.sh/(flag optional)` |
| 契約検証 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | ハード契約とポリシー検査 | `ERROR/WARN/INFO` / JSON summary |
| コンポーネント生成 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | component+variant 最小単位化 | build 可能なサービスディレクトリ |
| Bundle/Recipe レンダリング | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_bundle.py` / `validate_bundle.py` | 固定単一コンテナ複数サービス recipe を生成・検証 | プラットフォーム配布ディレクトリ |
| Compose/Vulhub-like import | `src/CloverSec-CTF-Build-Dockerizer/scripts/import_compose.py` | draft、renderable subset、import report を生成 | `scenario.draft.yaml` / `scenario.renderable.yaml` / `import-report.json` |
| check-service skeleton | `src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py` | HTTP/TCP/Redis/MySQL/SSH check 骨格を生成 | review-required `check/check.sh` |
| Linux-QEMU レンダリング | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | Docker 内 QEMU guest 配布物を生成 | 単一イメージ配布ディレクトリ |
| Linux-QEMU manual validation | `scripts/linux_qemu_manual_check.sh` | preflight/static/build/boot/flag/full 検証 | JSON summary / evidence notes |
| シナリオ生成 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | ローカル複数サービス編成を生成 | service dir + `docker-compose.yml` |
| シナリオ検証 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | mode/profile/port/AWDP 契約検査 | pass/fail |
| 例回帰 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | examples/scenario 一括回帰 | 集計レポート |
| スモークテスト | `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` | build レベルの高速回帰 | pass/fail |
| 実例プール回帰 | `scripts/validate_build_test.py` | Build_test cases を expected pass/fail で検証 | structured summary |
| リリース梱包 | `scripts/release_build.sh` / `scripts/publish_release.sh` | アセット生成と公開 | zip/sbom/deps |

## ワンコマンド導入と Skill 検出

まず Skill 検出を確認し、その後インストールします。

```bash
npx -y skills add . --list

npx -y skills add \
  https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill \
  --skill cloversec-ctf-build-dockerizer \
  --agent codex -y
```

導入後は examples を 1 本通しで実行し、Docker とスクリプト依存がローカルで正常か確認してください。

### Codex UI 表示戦略

Codex UI における Skill カードの表示内容は `src/CloverSec-CTF-Build-Dockerizer/agents/openai.yaml` で制御します。主に次の項目を定義します。

- `display_name`：UI 上のカードタイトル
- `short_description`：タイトル下のサブ説明
- `brand_color`：カードのブランドカラー
- `default_prompt`：試用・起動時に入る既定プロンプト
- `allow_implicit_invocation`：条件一致時にモデルが暗黙起動できるか

現在の既定プロンプト戦略は、先に技術スタックと `profile` を自動検出し、その後に準拠した `Dockerfile` / `start.sh` / `changeflag.sh` を生成し、最後に `validate` と配布ガイダンスを実行するという流れです。この層は Codex UI での見え方と起動方法だけに影響し、`render.py`、`validate.sh`、`render_component.py`、`render_scenario.py` の実行時挙動は変えません。

後で Codex 上のカード名、短い説明、試用プロンプトを調整したい場合は、README 本文より先にこのファイルを編集してください。

```yaml
interface:
  display_name: "CloverSec CTF Build Dockerizer"
  short_description: "标准化题目容器交付、BaseUnit/Linux-QEMU 构建与 Scenario 编排"
  default_prompt: "Use $cloversec-ctf-build-dockerizer to处理当前题目目录，先自动探测技术栈与 profile，再生成合规的 Dockerfile/start.sh/changeflag.sh，并执行 validate 与交付建议。"
```

## クイックスタート

### Agent-Orchestrated フロー（推奨）

標準プロンプト：

```text
CloverSec-CTF-Build-Dockerizer を使って現在の問題ディレクトリを処理してください。
まず intake/propose を実行し、evidence と input_audit 付きの CONFIG PROPOSAL を出力してください。
私が OK したら accept、render、validate を実行してください。
```

ショートプロンプト：

```text
この src は CTF 問題のソースです。プラットフォーム契約準拠の配布物を作ってください。
```

### 手動コマンドチェーン

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py intake --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py propose --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py accept --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py render --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py validate --project-dir .
```

### ランタイムプロファイル選択（PHP/Node/Java）

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config challenge.yaml \
  --runtime-profile php74-apache \
  --output .
```

イメージ優先順位：`--base-image > --runtime-profile > challenge.base_image > infer/default`。

## AI コーディング実践ガイド

各ツールごとに「呼び出し方」「推奨プロンプト」「再試行プロンプト」「検収コマンド」を統一形式で示します。

### Codex

呼び出し方：リポジトリルートで「提案 -> 確認 -> レンダリング -> 検証」の順序を明示。

推奨プロンプト：

```text
現在のディレクトリを CloverSec-CTF-Build-Dockerizer で処理してください。
まず derive_config.py を実行して evidence 付き CONFIG PROPOSAL を出力。
私の確認後に render + validate + smoke を実行し、失敗修正を報告してください。
対象モード: <jeopardy|rdg|awd|awdp|secops|baseunit|scenario>
```

再試行プロンプト：

```text
全体をやり直さず、現行 ERROR の最小修正のみ実施してください。
必要最小限の再検証だけ実行し、変更ファイルと結果を報告してください。
```

検収コマンド：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
```

### Cursor

呼び出し方：編集前に `challenge.yaml` / `scenario.yaml` を読ませる。

推奨プロンプト：

```text
既存スクリプト（render.py/validate.sh）を必ず利用し、手書き置換をしないでください。
CONFIG PROPOSAL を先に提示し、OK 後にレンダリングへ進んでください。
最終的に Dockerfile/start.sh/changeflag.sh 契約を満たしてください。
```

再試行プロンプト：

```text
通過済み部分は変更せず、今回失敗分のみ修正してください。
再検証コマンドをそのまま貼れる形で提示してください。
```

検収コマンド：

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### Trae

呼び出し方：4 段階（提案確認 -> レンダリング -> 検証 -> 振り返り）を固定。

推奨プロンプト：

```text
あなたは配布エンジニアです。
Phase1: derive_config と evidence を提示。
Phase2: 私の確認後に render 実行。
Phase3: validate/smoke 実行。
Phase4: 残リスクとリリース前確認項目を提示。
```

再試行プロンプト：

```text
失敗を「設定」「テンプレート」「実行時」に分類し、
1分類ずつ修正して即時再検証してください。
```

検収コマンド：

```bash
npx -y skills add . --list
bash scripts/release_build.sh --with-smoke
```

### Claude Code

呼び出し方：計画、実装、コマンド結果要約を明示要求。

推奨プロンプト：

```text
このリポジトリで V2 配布フローを実行してください:
1) derive_config -> CONFIG PROPOSAL
2) render.py / render_component.py / render_scenario.py（モードに応じて）
3) validate.sh / validate_scenario.py / smoke_test.sh
4) 失敗原因、修正内容、残リスクを要約
```

再試行プロンプト：

```text
通過済み手順は無視し、最新失敗コマンドに集中してください。
根因説明の後、最小パッチを適用して再検証してください。
```

検収コマンド：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### GitHub Copilot Chat

呼び出し方：VS Code 上で「既存スクリプト限定」を最初に固定。

推奨プロンプト：

```text
このリポジトリの既存スクリプト（derive_config/render/validate）のみで実行してください。
Dockerfile を一から書き直さないでください。
先に CONFIG PROPOSAL を提示し、確認後に次工程へ進んでください。
```

再試行プロンプト：

```text
端末エラーごとに該当ファイル/行を示し、
影響範囲のみ修正して再検証してください。
```

検収コマンド：

```bash
bash scripts/release_build.sh --with-smoke
```

### Aider

呼び出し方：先に失敗ログを作り、そのログをもとに限定修正。

推奨プロンプト：

```text
次の失敗ログをもとに修正してください。
目標チェック:
- bash scripts/doc_guard.sh
- bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
大規模リファクタは禁止、既存構成を維持してください。
```

再試行プロンプト：

```text
パッチ範囲が広すぎます。最小変更戦略に切り替えてください。
現在の失敗と直接関係するファイルだけを修正し、
各変更がどのエラーを解消するか対応付けて説明してください。
```

検収コマンド：

```bash
git diff --stat
bash scripts/doc_guard.sh
```

## 競技モード構築ガイド

### Jeopardy（Web / Pwn / AI）

通常の解題型配布。既定 profile は `jeopardy`。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/node-basic/challenge.yaml \
  --output /tmp/jeopardy-node

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/jeopardy-node/Dockerfile \
  /tmp/jeopardy-node/start.sh \
  /tmp/jeopardy-node/challenge.yaml
```

### Linux-QEMU（Linux kernel CVE / LPE）

特定 guest kernel、initrd/rootfs、kernel module、kernel config が必要な問題向けです。プラットフォームへの配布は単一 Docker イメージのまま維持し、`/start.sh` がコンテナ内で QEMU を起動し、脆弱環境は guest 内で動作します。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/linux-qemu-basic/challenge.yaml \
  --output /tmp/linux-qemu-basic

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/linux-qemu-basic/Dockerfile \
  /tmp/linux-qemu-basic/start.sh \
  /tmp/linux-qemu-basic/challenge.yaml
```

配布メモ：

- `guest_forwards[*].proto` は現在のリリースでも TCP のみ対応します。この制約は `v2.1.0` で導入されました。
- 既定の smoke は placeholder sample の render/validate までです。完全な QEMU boot と exploit 再現は実 VM アセットで検証します。
- `flag_injection=debugfs` では、`changeflag.sh` が guest flag path を rootfs image に書き込む必要があります。

manual validation entrypoint：

```bash
bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir /path/to/linux-qemu/code
bash scripts/linux_qemu_manual_check.sh --mode boot --case-dir /path/to/linux-qemu/code --host-port 2222
```

検証レベル、TCG/KVM 境界、動的 flag 書き込み、PoC 証拠記録は `src/CloverSec-CTF-Build-Dockerizer/docs/linux_qemu_manual_validation.md` を参照してください。

### RDG

防御運用 + check_service 方式向け。通常 `stack=rdg` を使用。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/rdg-python-ssti-basic/challenge.yaml \
  --output /tmp/rdg-python

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/rdg-python/Dockerfile \
  /tmp/rdg-python/start.sh \
  /tmp/rdg-python/challenge.yaml
```

`generate_check_stub.py` で HTTP/TCP/Redis/MySQL/SSH の編集可能な check-service skeleton を生成できます。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py \
  --type http \
  --output /tmp/rdg-python/check/check.sh \
  --target-port 8080 \
  --path /
```

生成物には `CHECK_REVIEW_REQUIRED` が入ります。実際の check logic を確認してから削除してください。

### AWD

攻防戦向け。既存 stack に `profile=awd` を重ねて実装。

重要：本プロジェクトは `stack=awd` を新設しません。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

上記は scenario/compose 構造だけを検証します。各 service ディレクトリにも `validate.sh` を実行する場合は `--validate-rendered` を追加します。

一括回帰入口の `validate_examples.sh` と `smoke_test.sh` は、scenario 例に対して既定で逐 service の交付検証を実行します。軽量な scenario/compose 構造検証だけにする場合は `SCENARIO_VALIDATE_RENDERED=0` を設定します。

### AWDP

attack + fix 向け。直接 SSH 修正ではなく、パッチバンドル提出方式。

固定契約：

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

セキュリティ運用・ハードニング課題向け。

重要：`stack=secops + profile=secops` は RDG 流用ではなく独立モデル。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/secops-nginx-basic/challenge.yaml \
  --output /tmp/secops-nginx

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/secops-nginx/Dockerfile \
  /tmp/secops-nginx/start.sh \
  /tmp/secops-nginx/challenge.yaml
```

### BaseUnit（指定バージョンサービス最小単位）

特定サービス/バージョンを短時間で配布可能な基座として生成する用途。

初期 10 コンポーネント：`mysql`、`redis`、`sshd`、`ttyd`、`apache`、`nginx`、`tomcat`、`php-fpm`、`vsftpd`、`weblogic`。

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

固定された少数の単一コンテナ複数サービス旧環境向けです。BaseUnit は単一 component、Scenario はローカル複数サービス編成、Bundle は 1 つの Docker image 内に限定 Recipe をまとめる方式です。

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

非対応の組み合わせは `BUNDLE_UNSUPPORTED_COMBINATION` を返します。別 stack に自動変換しません。

### Vulhub-like 移行

Vulhub 風の複数サービス環境を「ローカル compose 編成 + 単一サービス納品」へ移行する手順。

境界：`docker-compose.yml` はローカル検証専用。最終納品は各サービス単位。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-vulhub-like-basic/scenario.yaml \
  --output /tmp/scenario-vulhub-like

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-vulhub-like
```

上記は scenario/compose 構造だけを検証します。各 service ディレクトリにも `validate.sh` を実行する場合は `--validate-rendered` を追加します。一括回帰では既定で逐 service の交付検証を行い、`SCENARIO_VALIDATE_RENDERED=0` で構造検証のみに戻せます。

既存 compose input から始める場合は、先に draft、renderable subset、import report を生成します。

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/import_compose.py \
  --compose docker-compose.yml \
  --scenario-name imported-lab \
  --output /tmp/imported-lab
```

## プラットフォーム硬契約と境界

すべてのレンダリング結果で以下が必須です。

- `Dockerfile` が存在。
- 実行可能な `start.sh` が存在。
- 実行可能な `changeflag.sh` が存在。
- イメージ内に `/bin/bash` が存在。
- Dockerfile に `EXPOSE` 宣言がある。
- `start.sh` は実サービスを起動し、空回し keepalive を使わない。

`flag` ルール：

- 既定では `flag` 必須。
- `include_flag_artifact=false` 指定時に限り `flag` 欠落のみ許可。
- `changeflag.sh` 欠落は常に不可。

Scenario 境界：

- `docker-compose.yml` はローカル編成検証で利用可能。
- プラットフォーム最終納品は引き続き単一サービスディレクトリ（`Dockerfile + start.sh + changeflag.sh`）。

## Workflow スクリーンショット（プロンプトから公開まで）

Prompt 入力：

![workflow-01](docs/assets/readme/workflow-01-quick-prompt.png)

提案確認：

![workflow-02](docs/assets/readme/workflow-02-prebuild-decision.png)

エラー収束：

![workflow-03](docs/assets/readme/workflow-03-error-closure.png)

自動生成：

![workflow-04](docs/assets/readme/workflow-04-auto-build.png)

自動検証：

![workflow-05](docs/assets/readme/workflow-05-auto-validation.png)

硬契約チェック：

![workflow-06](docs/assets/readme/workflow-06-hard-check.png)

配布チェックリスト：

![workflow-07](docs/assets/readme/workflow-07-delivery-checklist.png)

## Build_test 実例

`Build_test/` は、実際の問題ケースを再現可能な build/validate フローで管理するためのディレクトリです。

| ディレクトリ | スタック | ポート | 起動コマンド | 主要ファイル |
|---|---|---:|---|---|
| `Build_test/CTF-NodeJs RCE-Test1` | node | 3000 | `node app.js` | `challenge.yaml` `Dockerfile` `start.sh` `app.js` |
| `Build_test/CTF-Python沙箱逃逸-Test2` | python | 5000 | `python app.py` | `challenge.yaml` `Dockerfile` `start.sh` `Build_test/CTF-Python沙箱逃逸-Test2/src/app.py` |

再検証コマンド：

```bash
cd "Build_test/CTF-NodeJs RCE-Test1"
npm ci
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## ファイル単位ディレクトリ索引

### ルート

| ファイル/ディレクトリ | 役割 |
|---|---|
| `README.md` | 中国語完全マニュアル（既定入口） |
| `README.en.md` | 英語完全マニュアル |
| `README.ja.md` | 日本語完全マニュアル |
| `VERSION` | 現在バージョン |
| `CHANGELOG.md` | 変更履歴 |
| `LICENSE` | ライセンス |
| `Build_test/` | 実例回帰ケース |
| `dist/` | リリース生成アセット |

### `scripts/`

| ファイル | 役割 |
|---|---|
| `scripts/doc_guard.py` | 文書整合性ゲート本体 |
| `scripts/doc_guard.sh` | doc guard エントリ |
| `scripts/release_build.py` | リリース梱包本体 |
| `scripts/release_build.sh` | 梱包エントリ |
| `scripts/publish_guard.py` | 公開前 version/白名单ガード |
| `scripts/publish_release.sh` | commit + push + tag + release 編成 |
| `scripts/validate_build_test.py` | Build_test 実例プール回帰 |
| `scripts/linux_qemu_manual_check.sh` | Linux-QEMU release/manual validation |
| `scripts/generate_sbom.py` | SBOM 生成本体 |
| `scripts/generate_sbom.sh` | SBOM エントリ |
| `scripts/sync.py` | ソース同期ロジック |
| `scripts/sync.sh` | 同期エントリ |

### `src/CloverSec-CTF-Build-Dockerizer/data`

| ファイル | 役割 |
|---|---|
| `schema.md` | `challenge.yaml` 契約 |
| `scenario_schema.md` | `scenario.yaml` 契約 |
| `bundle_schema.md` / `bundle_recipes.yaml` | Bundle/Recipe 契約と固定 recipe 定義 |
| `stacks.yaml` | スタック既定値 |
| `profiles.yaml` | profile 既定挙動 |
| `components.yaml` | BaseUnit component + variant 定義 |
| `runtime_profiles.yaml` | ランタイムプロファイル定義 |
| `patterns.yaml` | 自動検出ルール |
| `validate_rules.yaml` | `validate.sh` ルール |
| `validate_scenario_rules.yaml` | `validate_scenario.py` ルール |
| `base_image_allowlist.yaml` | 基底イメージ許可リスト |
| `README.md` | data 説明 |

### `src/CloverSec-CTF-Build-Dockerizer/scripts`

| ファイル | 役割 |
|---|---|
| `derive_config.py` | 提案生成 |
| `audit_input.py` | 入力リスク監査 |
| `workflow.py` | stateful intake/propose/accept/render/validate/status 編成 |
| `parse_config_block.py` | 提案解析 |
| `render.py` | 単体レンダリング |
| `render_component.py` | BaseUnit レンダリング |
| `render_bundle.py` / `validate_bundle.py` | Bundle/Recipe レンダリングと検証 |
| `import_compose.py` | compose/Vulhub-like import draft |
| `generate_check_stub.py` | RDG/SecOps check-service skeleton 生成 |
| `render_scenario.py` | シナリオレンダリング |
| `validate.sh` | 単体契約検証 |
| `validate_scenario.py` | シナリオ契約検証 |
| `validate_examples.sh` | 例一括回帰 |
| `smoke_test.sh` | スモーク回帰 |
| `validate_context.py` | challenge 文脈解析補助 |
| `autofix.py` | 自動修正補助 |
| `detect_stack.py` | スタック検出補助 |
| `utils.py` | 共通ユーティリティ |
| `cleanup_test_containers.sh` | テストコンテナ掃除 |
| `test_runtime_profiles.sh` | runtime profile 回帰 |
| `README.md` | scripts 説明 |

### `src/CloverSec-CTF-Build-Dockerizer/templates`

| パス | 役割 |
|---|---|
| `templates/node|php|python|java|tomcat|lamp|pwn|ai/` | Jeopardy テンプレート |
| `templates/rdg/` | RDG 専用テンプレート |
| `templates/secops/` | SecOps 専用テンプレート |
| `templates/baseunit/` | BaseUnit 共通テンプレート |
| `templates/linux-qemu/` | Linux kernel CVE/LPE 向け QEMU guest テンプレート |
| `templates/snippets/` | defense/check/changeflag 断片 |
| `templates/README.md` | templates 説明 |

### `src/CloverSec-CTF-Build-Dockerizer/examples`

| パス | 役割 |
|---|---|
| `examples/*-basic` | 単一問題の最小例 |
| `examples/node-awdp-basic` | AWDP 単体契約例 |
| `examples/secops-*-basic` | SecOps 例 |
| `examples/baseunit-*` | BaseUnit 例 |
| `examples/bundle-*` | Bundle/Recipe 例 |
| `examples/linux-qemu-basic` | placeholder VM アセット付き Linux-QEMU 例 |
| `examples/scenario-awd-basic` | AWD scenario 例 |
| `examples/scenario-awdp-basic` | AWDP scenario 例 |
| `examples/scenario-vulhub-like-basic` | Vulhub-like 移行例 |
| `examples/scenario-compose-import-basic` | compose import draft 例 |
| `examples/README.md` | examples 説明 |

### `src/CloverSec-CTF-Build-Dockerizer/docs`

| ファイル | 役割 |
|---|---|
| `architecture_overview.md` | アーキテクチャ概要 |
| `platform_contract.md` | プラットフォーム契約 |
| `orchestrated_workflow.md` | CONFIG PROPOSAL、OK gate、5 項確認 |
| `stack_cookbook.md` | スタック構築手引き |
| `validation_guide.md` | 検証ルール、check-service gate、release checks |
| `directory_guide.md` | ディレクトリ設計説明 |
| `linux_qemu_manual_validation.md` | Linux-QEMU manual/release validation guide |
| `bundle_design.md` | Bundle/Recipe 設計境界 |
| `troubleshooting.md` | 障害対応手引き |
| `beginner_guide.md` | 初学者向けガイド |

## FAQ とトラブルシュート

### Q1：なぜ `/start.sh`、`/changeflag.sh`、`/bin/bash` が必須ですか？

これはプラットフォーム実行契約です。いずれか欠けると起動やリセットが破綻します。

### Q2：`include_flag_artifact=false` を指定したのにエラーになります。

緩和されるのは `flag` のみです。`changeflag.sh` の欠落は許可されません。

### Q3：AWD と SecOps の使い分けは？

- 攻防運用主体なら「既存 stack + `profile=awd`」。
- 加固運用主体なら `stack=secops + profile=secops`。

### Q4：AWDP が直接 SSH 修正方式ではない理由は？

AWDP の本質は「パッチ提出と監査」です。`patch/src + patch.sh + tar.gz` を提出し、平台側で自動適用します。

### Q5：Scenario の compose をそのまま最終納品できない理由は？

対象プラットフォームは単一サービス納品前提だからです。compose はローカル検証専用です。

### Q6：`npx -y skills add . --list` は Release 資産に依存しますか？

依存しません。前者は Skill 検出、後者は配布アーカイブです。

## 保守・貢献・リリース

リリース前の最小チェック：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh --with-smoke
```

正式公開：

```bash
bash scripts/publish_release.sh --version v2.2.0
```

リモート tag/release 競合や認証失敗が出た場合は、その時点で停止し、先に阻害要因を解消してください。

## License

本プロジェクトは [MIT License](LICENSE) の下で提供されます。

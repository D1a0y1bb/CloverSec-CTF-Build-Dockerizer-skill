#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/generate_sbom.sh --source-dir <dir> --output-prefix <dist/prefix>

Outputs:
  <prefix>.sbom.spdx.json
  <prefix>.sbom.cdx.json
  <prefix>.deps.txt
USAGE
}

SOURCE_DIR=""
OUTPUT_PREFIX=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-dir)
      [[ $# -ge 2 ]] || { echo "[ERROR] --source-dir requires a value" >&2; exit 2; }
      SOURCE_DIR="$2"
      shift 2
      ;;
    --output-prefix)
      [[ $# -ge 2 ]] || { echo "[ERROR] --output-prefix requires a value" >&2; exit 2; }
      OUTPUT_PREFIX="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$SOURCE_DIR" ]] || { echo "[ERROR] missing --source-dir" >&2; exit 2; }
[[ -n "$OUTPUT_PREFIX" ]] || { echo "[ERROR] missing --output-prefix" >&2; exit 2; }
[[ -d "$SOURCE_DIR" ]] || { echo "[ERROR] source-dir not found: $SOURCE_DIR" >&2; exit 2; }

SPDX_OUT="${OUTPUT_PREFIX}.sbom.spdx.json"
CDX_OUT="${OUTPUT_PREFIX}.sbom.cdx.json"
DEPS_OUT="${OUTPUT_PREFIX}.deps.txt"

mkdir -p "$(dirname "$SPDX_OUT")"

write_placeholder_json() {
  local out_file="$1"
  local format_name="$2"
  local reason="$3"
  python3 - "$out_file" "$format_name" "$reason" <<'PY'
import json
import sys
from datetime import datetime, timezone

out = sys.argv[1]
fmt = sys.argv[2]
reason = sys.argv[3]
payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "format": fmt,
    "status": "placeholder",
    "reason": reason,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

generate_deps_report() {
  local source_dir="$1"
  local out_file="$2"
  python3 - "$source_dir" "$out_file" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(sys.argv[2])

lines = []
lines.append("# CloverSec release dependency summary")
lines.append(f"source_dir: {src}")

stacks_yaml = src / "data" / "stacks.yaml"
if stacks_yaml.exists():
    try:
        import yaml
        raw = yaml.safe_load(stacks_yaml.read_text(encoding="utf-8")) or {}
        stacks = raw.get("stacks", []) if isinstance(raw, dict) else []
        lines.append("")
        lines.append("[base_images]")
        for item in stacks:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id", "")).strip()
            defaults = item.get("defaults", {}) if isinstance(item.get("defaults"), dict) else {}
            base = str(defaults.get("base_image", "")).strip()
            if sid and base:
                lines.append(f"- {sid}: {base}")
    except Exception as exc:
        lines.append("")
        lines.append(f"[warn] failed to parse stacks.yaml: {exc}")

patterns = [
    "**/requirements.txt",
    "**/package.json",
    "**/pyproject.toml",
    "**/pom.xml",
    "**/build.gradle",
    "**/build.gradle.kts",
]
lines.append("")
lines.append("[manifest_files]")
seen = 0
for pat in patterns:
    for p in sorted(src.glob(pat)):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(src)
        except ValueError:
            rel = p
        lines.append(f"- {rel}")
        seen += 1
if seen == 0:
    lines.append("- (none)")

out.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

generate_deps_report "$SOURCE_DIR" "$DEPS_OUT"

have_syft=0
if command -v syft >/dev/null 2>&1; then
  have_syft=1
fi

if [[ "$have_syft" -eq 1 ]]; then
  if ! syft "dir:${SOURCE_DIR}" -o spdx-json > "$SPDX_OUT" 2>/dev/null; then
    write_placeholder_json "$SPDX_OUT" "spdx-json" "syft failed to generate SPDX"
  fi
  if ! syft "dir:${SOURCE_DIR}" -o cyclonedx-json > "$CDX_OUT" 2>/dev/null; then
    write_placeholder_json "$CDX_OUT" "cyclonedx-json" "syft failed to generate CycloneDX"
  fi
else
  have_docker_sbom=0
  if command -v docker >/dev/null 2>&1 && docker sbom --help >/dev/null 2>&1; then
    have_docker_sbom=1
  fi

  if [[ "$have_docker_sbom" -eq 1 ]]; then
    tmp_tag="cloversec-sbom-tmp:$(date +%s)-$RANDOM"
    tmp_ctx="$(mktemp -d)"
    trap 'rm -rf "$tmp_ctx" >/dev/null 2>&1 || true; docker rmi "$tmp_tag" >/dev/null 2>&1 || true' EXIT
    cat > "${tmp_ctx}/Dockerfile" <<'DF'
FROM alpine:3.20
WORKDIR /payload
COPY . /payload
DF
    rsync -a --delete "$SOURCE_DIR/" "$tmp_ctx/payload/" >/dev/null 2>&1 || cp -R "$SOURCE_DIR/." "$tmp_ctx/payload/"

    if docker build -q -t "$tmp_tag" "$tmp_ctx" >/dev/null 2>&1; then
      if ! docker sbom --format spdx-json "$tmp_tag" > "$SPDX_OUT" 2>/dev/null; then
        write_placeholder_json "$SPDX_OUT" "spdx-json" "docker sbom failed for SPDX"
      fi
      if ! docker sbom --format cyclonedx-json "$tmp_tag" > "$CDX_OUT" 2>/dev/null; then
        write_placeholder_json "$CDX_OUT" "cyclonedx-json" "docker sbom failed for CycloneDX"
      fi
    else
      write_placeholder_json "$SPDX_OUT" "spdx-json" "docker build failed for sbom fallback"
      write_placeholder_json "$CDX_OUT" "cyclonedx-json" "docker build failed for sbom fallback"
    fi
    rm -rf "$tmp_ctx" >/dev/null 2>&1 || true
    docker rmi "$tmp_tag" >/dev/null 2>&1 || true
    trap - EXIT
  else
    write_placeholder_json "$SPDX_OUT" "spdx-json" "no syft/docker sbom available"
    write_placeholder_json "$CDX_OUT" "cyclonedx-json" "no syft/docker sbom available"
  fi
fi

[[ -f "$SPDX_OUT" ]] || { echo "[ERROR] missing output: $SPDX_OUT" >&2; exit 1; }
[[ -f "$CDX_OUT" ]] || { echo "[ERROR] missing output: $CDX_OUT" >&2; exit 1; }
[[ -f "$DEPS_OUT" ]] || { echo "[ERROR] missing output: $DEPS_OUT" >&2; exit 1; }

echo "[OK] SBOM generated:"
echo "  - $SPDX_OUT"
echo "  - $CDX_OUT"
echo "  - $DEPS_OUT"

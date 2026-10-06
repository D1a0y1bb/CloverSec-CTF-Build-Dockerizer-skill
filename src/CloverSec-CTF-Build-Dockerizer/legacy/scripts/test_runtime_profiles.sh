#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DERIVE="${SCRIPT_DIR}/derive_config.py"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_case() {
  local name="$1"
  local dir="$2"
  local expected_profile="$3"
  local expected_image="$4"

  python3 "${DERIVE}" --project-dir "${dir}" --format json --pretty > "${TMP_DIR}/${name}.json"

  python3 - "${TMP_DIR}/${name}.json" "${expected_profile}" "${expected_image}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
exp_profile = sys.argv[2]
exp_image = sys.argv[3]

profile = str(payload.get("recommended_profile", ""))
image = str(payload.get("recommended_base_image", ""))

if profile != exp_profile:
    raise SystemExit(f"expected profile={exp_profile}, got={profile}")
if image != exp_image:
    raise SystemExit(f"expected image={exp_image}, got={image}")
PY

  echo "[OK] ${name}: profile=${expected_profile} image=${expected_image}"
}

mkdir -p "${TMP_DIR}/php_case"
cat > "${TMP_DIR}/php_case/composer.json" <<'JSON'
{
  "require": {
    "php": "^5.6"
  }
}
JSON

mkdir -p "${TMP_DIR}/node_case"
cat > "${TMP_DIR}/node_case/package.json" <<'JSON'
{
  "name": "demo",
  "version": "1.0.0",
  "engines": {
    "node": ">=14 <16"
  }
}
JSON

mkdir -p "${TMP_DIR}/java_case"
cat > "${TMP_DIR}/java_case/pom.xml" <<'XML'
<project>
  <modelVersion>4.0.0</modelVersion>
  <properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>
  </properties>
</project>
XML

run_case "php" "${TMP_DIR}/php_case" "php56-apache" "php:5.6-apache"
run_case "node" "${TMP_DIR}/node_case" "node14-bullseye" "node:14-bullseye"
run_case "java" "${TMP_DIR}/java_case" "temurin8-jre-jammy" "eclipse-temurin:8-jre-jammy"

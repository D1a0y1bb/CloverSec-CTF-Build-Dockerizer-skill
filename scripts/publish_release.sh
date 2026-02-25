#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="${ROOT_DIR}/VERSION"
CHANGELOG_FILE="${ROOT_DIR}/CHANGELOG.md"
RELEASE_BUILD_SCRIPT="${ROOT_DIR}/scripts/release_build.sh"
PACKAGE_NAME="CloverSec-CTF-Build-Dockerizer"

SOURCE_DIR=""
RELEASE_NOTES_FILE=""
SKIP_CHECKS="false"
SKIP_RELEASE="false"
SKIP_UPLOAD="false"
DRY_RUN="false"
COMMIT_MESSAGE=""
VERSION_OVERRIDE=""

VERSION=""
CURRENT_BRANCH=""
ZIP_PATH=""
OWNER_REPO=""
RELEASE_ID=""
RELEASE_HTML_URL=""
ASSET_DOWNLOAD_URL=""
RELEASE_IS_DRAFT=""
RELEASE_IS_IMMUTABLE=""
RELEASE_TAG_NAME=""
AUTH_ARGS=()
PUBLISH_STAGE_PATHS=()

log() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/publish_release.sh [options]

What this script does:
  1) Optional: rsync from a private source repo (excluding internal/)
  2) Build release artifact via scripts/release_build.sh
  3) Commit and push current branch
  4) Create/push git tag from VERSION
  5) Create or update GitHub Release (immutable-friendly: draft first)
  6) Upload dist/CloverSec-CTF-Build-Dockerizer-<VERSION>.zip as release asset
  7) Publish draft release

Options:
  --source-dir <path>     Sync files from source repo before publishing
  --version <vX.Y.Z>      Override VERSION for this run (also writes VERSION file)
  --notes-file <path>     Use custom release notes file
  --commit-message <msg>  Commit message (default: "release: <VERSION>")
  --skip-checks           Pass --skip-checks to scripts/release_build.sh
  --skip-release          Skip GitHub Release create/update and asset upload
  --skip-upload           Create/update release but skip asset upload
  --dry-run               Validate and build only; skip commit/push/tag/release
  -h, --help              Show help

Examples:
  bash scripts/publish_release.sh --source-dir /path/to/source-repo
  bash scripts/publish_release.sh --version v1.3.0
  bash scripts/publish_release.sh --notes-file /tmp/release_notes.md
USAGE
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "Missing required command: ${cmd}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --source-dir)
        [[ $# -ge 2 ]] || die "--source-dir requires a path"
        SOURCE_DIR="$2"
        shift 2
        ;;
      --version)
        [[ $# -ge 2 ]] || die "--version requires a value"
        VERSION_OVERRIDE="$2"
        shift 2
        ;;
      --notes-file)
        [[ $# -ge 2 ]] || die "--notes-file requires a path"
        RELEASE_NOTES_FILE="$2"
        shift 2
        ;;
      --commit-message)
        [[ $# -ge 2 ]] || die "--commit-message requires text"
        COMMIT_MESSAGE="$2"
        shift 2
        ;;
      --skip-checks)
        SKIP_CHECKS="true"
        shift
        ;;
      --skip-release)
        SKIP_RELEASE="true"
        shift
        ;;
      --skip-upload)
        SKIP_UPLOAD="true"
        shift
        ;;
      --dry-run)
        DRY_RUN="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

load_version() {
  if [[ -n "${VERSION_OVERRIDE}" ]]; then
    VERSION="${VERSION_OVERRIDE}"
    printf '%s\n' "${VERSION}" > "${VERSION_FILE}"
    log "VERSION updated to ${VERSION} from --version"
  else
    [[ -f "${VERSION_FILE}" ]] || die "VERSION file not found: ${VERSION_FILE}"
    VERSION="$(tr -d '[:space:]' < "${VERSION_FILE}")"
  fi

  [[ -n "${VERSION}" ]] || die "Version is empty"
  [[ "${VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$ ]] || die "Invalid VERSION format: ${VERSION}"
}

validate_workspace() {
  git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not a git repository: ${ROOT_DIR}"
  CURRENT_BRANCH="$(git -C "${ROOT_DIR}" branch --show-current)"
  [[ -n "${CURRENT_BRANCH}" ]] || die "Cannot detect current branch"
  [[ -f "${RELEASE_BUILD_SCRIPT}" ]] || die "Missing script: ${RELEASE_BUILD_SCRIPT}"
}

sync_from_source() {
  [[ -n "${SOURCE_DIR}" ]] || return 0

  if [[ "${SOURCE_DIR}" != /* ]]; then
    SOURCE_DIR="$(cd "${ROOT_DIR}" && cd "${SOURCE_DIR}" && pwd)"
  fi

  [[ -d "${SOURCE_DIR}" ]] || die "source-dir does not exist: ${SOURCE_DIR}"
  [[ "${SOURCE_DIR}" != "${ROOT_DIR}" ]] || die "source-dir must be different from publish repo"
  [[ -f "${SOURCE_DIR}/src/CloverSec-CTF-Build-Dockerizer/SKILL.md" ]] || die "source-dir is invalid (missing src/.../SKILL.md)"

  require_cmd rsync
  log "Syncing from source repo: ${SOURCE_DIR}"
  rsync -av --delete \
    --exclude '.git/' \
    --exclude 'internal/' \
    --exclude '.DS_Store' \
    "${SOURCE_DIR}/" "${ROOT_DIR}/"
}

build_release_zip() {
  local cmd=(bash "${RELEASE_BUILD_SCRIPT}")
  if [[ "${SKIP_CHECKS}" == "true" ]]; then
    cmd+=(--skip-checks)
  fi

  log "Building release artifact with ${cmd[*]}"
  "${cmd[@]}"

  ZIP_PATH="${ROOT_DIR}/dist/${PACKAGE_NAME}-${VERSION}.zip"
  [[ -f "${ZIP_PATH}" ]] || die "Release zip not found: ${ZIP_PATH}"
}

is_blocked_publish_path() {
  local path="$1"
  case "${path}" in
    internal/*|dist/*|.DS_Store|*/.DS_Store|SESSION_SUMMARY_v1.2.2.md|*.pem|*.key|.env|.env.*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_allowed_publish_path() {
  local path="$1"
  case "${path}" in
    VERSION|CHANGELOG.md|README.md|README.zh-CN.md|README.en.md|LICENSE|.gitignore|scripts/*|src/CloverSec-CTF-Build-Dockerizer/*|docs/assets/readme/*|Build_test/*|.github/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

print_path_group() {
  local title="$1"
  shift
  local item
  echo "${title}"
  for item in "$@"; do
    echo "  - ${item}"
  done
}

collect_publish_stage_paths() {
  local entry
  local status
  local payload
  local extra_path
  local path
  local -a changed_paths=()
  local -a blocked_paths=()
  local -a unexpected_paths=()
  local -a allowed_paths=()

  # Use NUL-delimited porcelain output to keep spaces/special chars intact.
  while IFS= read -r -d '' entry; do
    [[ -n "${entry}" ]] || continue
    status="${entry:0:2}"
    payload="${entry:3}"
    changed_paths+=("${payload}")

    if [[ "${status:0:1}" == "R" || "${status:1:1}" == "R" || "${status:0:1}" == "C" || "${status:1:1}" == "C" ]]; then
      IFS= read -r -d '' extra_path || die "Failed to parse rename/copy path from git status"
      changed_paths+=("${extra_path}")
    fi
  done < <(git -C "${ROOT_DIR}" status --porcelain -z)

  if [[ ${#changed_paths[@]} -eq 0 ]]; then
    PUBLISH_STAGE_PATHS=()
    return 0
  fi

  for path in "${changed_paths[@]}"; do
    if is_blocked_publish_path "${path}"; then
      blocked_paths+=("${path}")
      continue
    fi
    if ! is_allowed_publish_path "${path}"; then
      unexpected_paths+=("${path}")
      continue
    fi
    allowed_paths+=("${path}")
  done

  if [[ ${#blocked_paths[@]} -gt 0 ]]; then
    print_path_group "[ERROR] 检测到阻断路径（不允许发布脚本自动提交）:" "${blocked_paths[@]}" >&2
    die "发布已中止，请先清理阻断路径。"
  fi

  if [[ ${#unexpected_paths[@]} -gt 0 ]]; then
    print_path_group "[ERROR] 检测到白名单外变更（请手动审查并提交）:" "${unexpected_paths[@]}" >&2
    die "发布已中止，请先处理白名单外变更。"
  fi

  PUBLISH_STAGE_PATHS=("${allowed_paths[@]}")
}

commit_and_push() {
  collect_publish_stage_paths

  if [[ "${DRY_RUN}" == "true" ]]; then
    if [[ ${#PUBLISH_STAGE_PATHS[@]} -eq 0 ]]; then
      log "Dry-run: no changes to commit"
    else
      print_path_group "[INFO] Dry-run: 白名单内可提交路径:" "${PUBLISH_STAGE_PATHS[@]}"
    fi
    log "Dry-run: skip commit and push"
    return 0
  fi

  if [[ ${#PUBLISH_STAGE_PATHS[@]} -eq 0 ]]; then
    log "No changes to commit"
  else
    git -C "${ROOT_DIR}" add -- "${PUBLISH_STAGE_PATHS[@]}"
  fi

  if git -C "${ROOT_DIR}" diff --cached --quiet; then
    log "No staged changes to commit"
  else
    if [[ -z "${COMMIT_MESSAGE}" ]]; then
      COMMIT_MESSAGE="release: ${VERSION}"
    fi
    git -C "${ROOT_DIR}" commit -m "${COMMIT_MESSAGE}"
  fi

  log "Pushing branch ${CURRENT_BRANCH} to origin"
  git -C "${ROOT_DIR}" push origin "${CURRENT_BRANCH}"
}

ensure_version_tag() {
  local head_commit
  local local_tag_commit
  local remote_tag_commit

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "Dry-run: skip tag checks and pushes"
    return 0
  fi

  head_commit="$(git -C "${ROOT_DIR}" rev-parse HEAD)"

  if git -C "${ROOT_DIR}" rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null; then
    local_tag_commit="$(git -C "${ROOT_DIR}" rev-list -n1 "${VERSION}")"
    [[ "${local_tag_commit}" == "${head_commit}" ]] || die "Local tag ${VERSION} points to ${local_tag_commit}, not HEAD ${head_commit}. Bump VERSION before publishing."
  else
    git -C "${ROOT_DIR}" tag -a "${VERSION}" -m "${VERSION}"
  fi

  remote_tag_commit="$(git -C "${ROOT_DIR}" ls-remote --tags origin "refs/tags/${VERSION}^{}" | awk 'NR==1{print $1}')"
  if [[ -z "${remote_tag_commit}" ]]; then
    remote_tag_commit="$(git -C "${ROOT_DIR}" ls-remote --tags origin "refs/tags/${VERSION}" | awk 'NR==1{print $1}')"
  fi

  if [[ -n "${remote_tag_commit}" && "${remote_tag_commit}" != "${head_commit}" ]]; then
    die "Remote tag ${VERSION} points to ${remote_tag_commit}, not HEAD ${head_commit}. Bump VERSION before publishing."
  fi

  if [[ -z "${remote_tag_commit}" ]]; then
    log "Pushing tag ${VERSION}"
    git -C "${ROOT_DIR}" push origin "${VERSION}"
  else
    log "Tag ${VERSION} already exists on remote and matches HEAD"
  fi
}

resolve_owner_repo() {
  local origin_url
  local path

  origin_url="$(git -C "${ROOT_DIR}" remote get-url origin)"

  case "${origin_url}" in
    https://github.com/*|http://github.com/*)
      path="${origin_url#*github.com/}"
      ;;
    git@github.com:*)
      path="${origin_url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      path="${origin_url#ssh://git@github.com/}"
      ;;
    *)
      die "origin is not a GitHub remote: ${origin_url}"
      ;;
  esac

  path="${path%.git}"
  [[ "${path}" =~ ^[^/]+/[^/]+$ ]] || die "Cannot parse owner/repo from origin: ${origin_url}"
  OWNER_REPO="${path}"
}

setup_auth() {
  local token
  local cred
  local user
  local pass

  token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if [[ -n "${token}" ]]; then
    AUTH_ARGS=(-H "Authorization: Bearer ${token}")
    return 0
  fi

  cred="$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill 2>/dev/null || true)"
  user="$(printf '%s\n' "${cred}" | awk -F= '/^username=/{print $2}')"
  pass="$(printf '%s\n' "${cred}" | awk -F= '/^password=/{print $2}')"

  [[ -n "${user}" && -n "${pass}" ]] || die "GitHub auth not found. Set GH_TOKEN/GITHUB_TOKEN or configure git credential for github.com."
  AUTH_ARGS=(-u "${user}:${pass}")
}

api_request() {
  local method="$1"
  local url="$2"
  local output_file="$3"
  local data_file="${4:-}"
  local content_type="${5:-application/json}"
  local code

  local curl_args=(
    -sS
    -o "${output_file}"
    -w '%{http_code}'
    -X "${method}"
    -H 'Accept: application/vnd.github+json'
    -H 'X-GitHub-Api-Version: 2022-11-28'
  )
  curl_args+=("${AUTH_ARGS[@]}")

  if [[ -n "${data_file}" ]]; then
    curl_args+=(-H "Content-Type: ${content_type}" --data-binary "@${data_file}")
  fi

  code="$(curl "${curl_args[@]}" "${url}")"
  echo "${code}"
}

extract_release_notes() {
  if [[ -n "${RELEASE_NOTES_FILE}" ]]; then
    [[ -f "${RELEASE_NOTES_FILE}" ]] || die "notes-file not found: ${RELEASE_NOTES_FILE}"
    cat "${RELEASE_NOTES_FILE}"
    return 0
  fi

  if [[ -f "${CHANGELOG_FILE}" ]]; then
    awk -v ver="${VERSION}" '
      $0 ~ "^##[[:space:]]*" ver "([[:space:]]|$|-)" {capture=1; next}
      capture && $0 ~ "^##[[:space:]]+" {exit}
      capture {print}
    ' "${CHANGELOG_FILE}"
  fi
}

json_read() {
  local json_file="$1"
  local expression="$2"
  python3 - "$json_file" "$expression" <<'PY'
import json
import sys

json_file = sys.argv[1]
expr = sys.argv[2]

obj = json.load(open(json_file, "r", encoding="utf-8"))

if expr == "release.id":
    print(obj.get("id", ""))
elif expr == "release.html_url":
    print(obj.get("html_url", ""))
elif expr == "release.upload_url":
    print(obj.get("upload_url", ""))
elif expr == "release.draft":
    print("true" if obj.get("draft", False) else "false")
elif expr == "release.immutable":
    print("true" if obj.get("immutable", False) else "false")
elif expr == "release.tag_name":
    print(obj.get("tag_name", ""))
elif expr.startswith("asset.id:"):
    name = expr.split(":", 1)[1]
    asset_id = ""
    for asset in obj.get("assets", []):
        if asset.get("name") == name:
            asset_id = str(asset.get("id", ""))
            break
    print(asset_id)
elif expr.startswith("asset.url:"):
    name = expr.split(":", 1)[1]
    asset_url = ""
    for asset in obj.get("assets", []):
        if asset.get("name") == name:
            asset_url = str(asset.get("browser_download_url", ""))
            break
    print(asset_url)
elif expr == "asset.browser_download_url":
    print(obj.get("browser_download_url", ""))
else:
    print("")
PY
}

refresh_release_state() {
  local response_file
  local code

  [[ -n "${RELEASE_ID}" ]] || die "release id is empty"

  response_file="$(mktemp)"
  code="$(api_request "GET" "https://api.github.com/repos/${OWNER_REPO}/releases/${RELEASE_ID}" "${response_file}")"
  [[ "${code}" == "200" ]] || die "Failed to fetch release state (HTTP ${code}): $(head -c 500 "${response_file}")"

  RELEASE_HTML_URL="$(json_read "${response_file}" "release.html_url")"
  RELEASE_IS_DRAFT="$(json_read "${response_file}" "release.draft")"
  RELEASE_IS_IMMUTABLE="$(json_read "${response_file}" "release.immutable")"
  RELEASE_TAG_NAME="$(json_read "${response_file}" "release.tag_name")"

  rm -f "${response_file}"
}

create_or_prepare_release() {
  local notes
  local notes_body
  local payload_file
  local response_file
  local code
  local release_api
  local get_api
  local update_api
  local create_api

  notes="$(extract_release_notes)"
  if [[ -z "$(printf '%s' "${notes}" | tr -d '[:space:]')" ]]; then
    notes="Release ${VERSION}"
  fi
  notes_body="$(printf '%s\n' "${notes}")"

  release_api="https://api.github.com/repos/${OWNER_REPO}/releases"
  get_api="${release_api}/tags/${VERSION}"

  response_file="$(mktemp)"
  code="$(api_request "GET" "${get_api}" "${response_file}")"

  payload_file="$(mktemp)"
  if [[ "${code}" == "200" ]]; then
    RELEASE_ID="$(json_read "${response_file}" "release.id")"
    [[ -n "${RELEASE_ID}" ]] || die "Cannot parse existing release id"
    RELEASE_HTML_URL="$(json_read "${response_file}" "release.html_url")"
    RELEASE_IS_DRAFT="$(json_read "${response_file}" "release.draft")"
    RELEASE_IS_IMMUTABLE="$(json_read "${response_file}" "release.immutable")"
    RELEASE_TAG_NAME="$(json_read "${response_file}" "release.tag_name")"

    # Published immutable release is append-only blocked: keep as-is and let
    # upload step decide whether existing asset is sufficient.
    if [[ "${RELEASE_IS_IMMUTABLE}" == "true" && "${RELEASE_IS_DRAFT}" != "true" ]]; then
      warn "Release ${VERSION} is immutable and already published; metadata update is skipped."
      rm -f "${payload_file}" "${response_file}"
      return 0
    fi

    python3 - "${VERSION}" "${notes_body}" "${RELEASE_IS_DRAFT}" <<'PY' > "${payload_file}"
import json
import sys
version = sys.argv[1]
notes = sys.argv[2]
draft = sys.argv[3].lower() == "true"
payload = {
    "name": version,
    "body": notes,
    "draft": draft,
    "prerelease": False
}
print(json.dumps(payload, ensure_ascii=False))
PY

    update_api="${release_api}/${RELEASE_ID}"
    code="$(api_request "PATCH" "${update_api}" "${response_file}" "${payload_file}")"
    [[ "${code}" == "200" ]] || die "Release update failed (HTTP ${code}): $(head -c 500 "${response_file}")"
    log "Updated release ${VERSION}"
  elif [[ "${code}" == "404" ]]; then
    python3 - "${VERSION}" "${CURRENT_BRANCH}" "${notes_body}" <<'PY' > "${payload_file}"
import json
import sys
version = sys.argv[1]
branch = sys.argv[2]
notes = sys.argv[3]
payload = {
    "tag_name": version,
    "target_commitish": branch,
    "name": version,
    "body": notes,
    "draft": True,
    "prerelease": False
}
print(json.dumps(payload, ensure_ascii=False))
PY

    create_api="${release_api}"
    code="$(api_request "POST" "${create_api}" "${response_file}" "${payload_file}")"
    if [[ "${code}" != "201" ]]; then
      if [[ "${code}" == "422" ]] && grep -q "tag_name was used by an immutable release" "${response_file}"; then
        die "Release create blocked: tag ${VERSION} has been consumed by an immutable release record. Please bump VERSION (for example vX.Y.Z-r1) and retry."
      fi
      die "Release create failed (HTTP ${code}): $(head -c 500 "${response_file}")"
    fi
    RELEASE_ID="$(json_read "${response_file}" "release.id")"
    log "Created draft release ${VERSION} (immutable-compatible flow)"
  else
    die "Release lookup failed (HTTP ${code}): $(head -c 500 "${response_file}")"
  fi

  RELEASE_HTML_URL="$(json_read "${response_file}" "release.html_url")"
  RELEASE_IS_DRAFT="$(json_read "${response_file}" "release.draft")"
  RELEASE_IS_IMMUTABLE="$(json_read "${response_file}" "release.immutable")"
  RELEASE_TAG_NAME="$(json_read "${response_file}" "release.tag_name")"

  rm -f "${payload_file}" "${response_file}"
}

upload_release_asset() {
  local asset_name
  local get_release_file
  local code
  local existing_asset_id
  local existing_asset_url
  local upload_response
  local upload_url

  [[ "${SKIP_UPLOAD}" == "false" ]] || { log "Skipped asset upload (--skip-upload)"; return 0; }
  [[ -f "${ZIP_PATH}" ]] || die "Cannot upload missing asset: ${ZIP_PATH}"

  asset_name="$(basename "${ZIP_PATH}")"

  get_release_file="$(mktemp)"
  code="$(api_request "GET" "https://api.github.com/repos/${OWNER_REPO}/releases/${RELEASE_ID}" "${get_release_file}")"
  [[ "${code}" == "200" ]] || die "Failed to fetch release before upload (HTTP ${code})"
  RELEASE_IS_DRAFT="$(json_read "${get_release_file}" "release.draft")"
  RELEASE_IS_IMMUTABLE="$(json_read "${get_release_file}" "release.immutable")"
  RELEASE_HTML_URL="$(json_read "${get_release_file}" "release.html_url")"
  RELEASE_TAG_NAME="$(json_read "${get_release_file}" "release.tag_name")"

  existing_asset_id="$(json_read "${get_release_file}" "asset.id:${asset_name}")"
  existing_asset_url="$(json_read "${get_release_file}" "asset.url:${asset_name}")"
  if [[ -n "${existing_asset_id}" ]]; then
    if [[ "${RELEASE_IS_IMMUTABLE}" == "true" && "${RELEASE_IS_DRAFT}" != "true" ]]; then
      ASSET_DOWNLOAD_URL="${existing_asset_url}"
      log "Immutable release already contains asset ${asset_name}; keeping existing asset"
      rm -f "${get_release_file}"
      return 0
    fi

    code="$(api_request "DELETE" "https://api.github.com/repos/${OWNER_REPO}/releases/assets/${existing_asset_id}" "${get_release_file}")"
    [[ "${code}" == "204" ]] || die "Failed to delete existing asset id=${existing_asset_id} (HTTP ${code})"
    log "Deleted existing asset: ${asset_name}"
  fi

  if [[ "${RELEASE_IS_IMMUTABLE}" == "true" && "${RELEASE_IS_DRAFT}" != "true" ]]; then
    die "Release ${VERSION} is immutable and published; cannot upload new asset ${asset_name}. Please bump VERSION and publish a new release."
  fi

  upload_response="$(mktemp)"
  upload_url="https://uploads.github.com/repos/${OWNER_REPO}/releases/${RELEASE_ID}/assets?name=${asset_name}"
  code="$(api_request "POST" "${upload_url}" "${upload_response}" "${ZIP_PATH}" "application/zip")"
  [[ "${code}" == "201" ]] || die "Asset upload failed (HTTP ${code}): $(head -c 500 "${upload_response}")"

  ASSET_DOWNLOAD_URL="$(json_read "${upload_response}" "asset.browser_download_url")"
  rm -f "${get_release_file}" "${upload_response}"
}

publish_release_if_needed() {
  local payload_file
  local response_file
  local code
  local update_api

  refresh_release_state

  if [[ "${RELEASE_IS_DRAFT}" != "true" ]]; then
    log "Release ${RELEASE_TAG_NAME:-${VERSION}} already published"
    return 0
  fi

  payload_file="$(mktemp)"
  python3 <<'PY' > "${payload_file}"
import json
print(json.dumps({"draft": False}, ensure_ascii=False))
PY

  response_file="$(mktemp)"
  update_api="https://api.github.com/repos/${OWNER_REPO}/releases/${RELEASE_ID}"
  code="$(api_request "PATCH" "${update_api}" "${response_file}" "${payload_file}")"
  [[ "${code}" == "200" ]] || die "Release publish failed (HTTP ${code}): $(head -c 500 "${response_file}")"

  RELEASE_HTML_URL="$(json_read "${response_file}" "release.html_url")"
  RELEASE_IS_DRAFT="$(json_read "${response_file}" "release.draft")"
  RELEASE_IS_IMMUTABLE="$(json_read "${response_file}" "release.immutable")"
  RELEASE_TAG_NAME="$(json_read "${response_file}" "release.tag_name")"
  [[ "${RELEASE_IS_DRAFT}" != "true" ]] || die "Release publish failed: release is still draft"

  rm -f "${payload_file}" "${response_file}"
  log "Published release ${RELEASE_TAG_NAME:-${VERSION}}"
}

main() {
  require_cmd git
  require_cmd python3
  require_cmd curl
  parse_args "$@"

  validate_workspace
  load_version
  sync_from_source
  build_release_zip
  commit_and_push
  ensure_version_tag

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "Done (dry-run)"
    exit 0
  fi

  if [[ "${SKIP_RELEASE}" == "true" ]]; then
    log "Done (release steps skipped by --skip-release)"
    exit 0
  fi

  resolve_owner_repo
  setup_auth
  create_or_prepare_release
  upload_release_asset
  publish_release_if_needed

  echo "[OK] Publish complete"
  echo "[OK] Version: ${VERSION}"
  echo "[OK] Release: ${RELEASE_HTML_URL}"
  if [[ -n "${ASSET_DOWNLOAD_URL}" ]]; then
    echo "[OK] Asset: ${ASSET_DOWNLOAD_URL}"
  fi
}

main "$@"

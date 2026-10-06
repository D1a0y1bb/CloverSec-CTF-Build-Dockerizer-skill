{{> snippets/start-header.tpl }}

# BaseUnit generic entrypoint for minimal service-pack delivery directories.
{{RDG_FLAG_START_BLOCK}}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"
{{DEFENSE_START_BLOCK}}

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD must not be empty for stack=baseunit." >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"

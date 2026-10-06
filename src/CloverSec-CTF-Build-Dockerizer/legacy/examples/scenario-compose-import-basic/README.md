# scenario-compose-import-basic

Compose import draft example. The importer writes a full audit draft and a renderable subset:

```bash
python3 ../../scripts/import_compose.py \
  --compose docker-compose.yml \
  --output /tmp/scenario-compose-import-basic \
  --scenario-name scenario-compose-import-basic
```

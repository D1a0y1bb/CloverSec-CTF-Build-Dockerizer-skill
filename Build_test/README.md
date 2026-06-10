# Build_test Real Case Pool

`Build_test/` stores real CTF and vulnerability environment samples for regression work that is too messy for `examples/`.

The pool intentionally contains both passing and failing cases. A failing Docker contract can still pass this regression when `cases.yaml` declares that failure as expected. This keeps historical inputs useful without pretending they are ready for platform release.

## Case Metadata

- `cases.yaml` is the machine-readable case list.
- Each case directory has `case_note.md` with source, expected route, verification level, and current limits.
- Large VM assets, archives, `.git`, `node_modules`, caches, and files over 20 MB must not be copied into this directory.

## Regression Commands

```bash
python3 scripts/validate_build_test.py
python3 scripts/validate_build_test.py --format json
python3 scripts/validate_build_test.py --case cpanel-whm-authbypass-rce
```

The script runs input audit for every case. When a case has `Dockerfile`, `start.sh`, and `challenge.yaml`, it can also run `validate.sh` and compare the result with the expected contract status in `cases.yaml`.

## Current Cases

| Case | Purpose | Contract |
|---|---|---|
| `node-rce-existing` | Existing Node.js sample with historical delivery gaps | expected fail |
| `python-sandbox-existing` | Existing Python sample with historical delivery gaps | expected fail |
| `cpanel-whm-authbypass-rce` | cPanel/WHM routing to bundle_recipe while Docker contract passes | expected pass |
| `linux-qemu-copy-fail-missing-assets` | Linux-QEMU missing VM assets and manual review route | expected fail |
| `web-push-boxs` | Clean Web input with historical Docker contract gaps | expected fail |
| `web-push-letters` | Clean Web input with historical Docker contract gaps | expected fail |
| `pwn-house-deploy` | Dirty Pwn input with compose/xinetd shape | skipped contract |
| `php-banfunc-compose` | Dirty PHP compose input | skipped contract |

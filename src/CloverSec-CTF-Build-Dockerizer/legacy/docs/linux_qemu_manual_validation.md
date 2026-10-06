# Linux-QEMU Manual Validation

Linux-QEMU challenges need a separate manual validation path. Default CI should keep using render and static validation only; full VM boot, guest flag injection, and exploit proof require an operator-controlled run.

## Validation Levels

| Level | Purpose | Typical command |
|---|---|---|
| static | Check delivery files, `challenge.vm`, VM assets, `hostfwd`, and Docker contract | `bash validate.sh Dockerfile start.sh challenge.yaml` |
| manual boot | Build the outer Docker image, boot QEMU, and verify guest service reachability | `bash scripts/linux_qemu_manual_check.sh --mode boot --case-dir ...` |
| challenge acceptance | Change dynamic flag inside guest rootfs and run the challenge PoC | `bash scripts/linux_qemu_manual_check.sh --mode full --case-dir ... --poc-cmd '...'` |

## Manual Script

Run preflight first. It does not build an image and does not start QEMU.

```bash
bash scripts/linux_qemu_manual_check.sh \
  --mode preflight \
  --case-dir "/path/to/linux-qemu/code" \
  --asset-manifest "/path/to/asset_manifest.yaml" \
  --json-summary /tmp/linux-qemu-preflight.json
```

Boot validation is explicit:

```bash
bash scripts/linux_qemu_manual_check.sh \
  --mode boot \
  --case-dir "/path/to/linux-qemu/code" \
  --image linux-qemu-manual:case-name \
  --host-port 2222 \
  --timeout-seconds 300 \
  --json-summary /tmp/linux-qemu-boot.json
```

Dynamic flag validation writes the flag through `/changeflag.sh` and then reads `/root/flag` from the guest rootfs with `debugfs` inside the container:

```bash
bash scripts/linux_qemu_manual_check.sh \
  --mode flag \
  --case-dir "/path/to/linux-qemu/code" \
  --flag "flag{manual-check}" \
  --json-summary /tmp/linux-qemu-flag.json
```

`--mode full` also runs `--poc-cmd` as a host-side command. The command receives `CASE_DIR`, `HOST_PORT`, `IMAGE`, `CONTAINER_NAME`, and `FLAG` in the environment.

## TCG, KVM, and Platform Boundaries

- Default to TCG for portability.
- KVM may be used only when the challenge explicitly asks for it and the platform exposes `/dev/kvm`.
- Do not assume `--privileged` is available on the target platform.
- Keep Docker `EXPOSE`, QEMU `hostfwd`, and platform port mapping consistent.
- Store heavy VM assets outside the Git repository unless a small placeholder is enough for static validation.

## Evidence to Keep

For manual validation, keep these artifacts outside the repository:

- `linux-qemu-*.json` summary from `scripts/linux_qemu_manual_check.sh`
- `asset_manifest.yaml` with VM asset paths, sizes, and SHA256 values
- Docker image tag or tar digest
- QEMU boot log excerpt
- hostfwd reachability evidence
- dynamic flag value and guest readback evidence
- PoC command and exit status

## Current Real-Asset Case

`Build_test/linux-qemu-real-fragnesia/manual_case.yaml` records a local real-asset case. `Build_test/linux-qemu-real-fragnesia/asset_manifest.yaml` records the external kernel, initrd, and rootfs size/SHA256 values. The VM rootfs is about 1.2 GB and is intentionally not copied into this repository.

Verify an external asset manifest before boot checks:

```bash
python3 scripts/verify_asset_manifest.py --manifest /path/to/asset_manifest.yaml
```

## Adding Another CVE Case

Keep new Linux-QEMU CVE cases small and evidence-based. A case can be promoted from candidate to real-asset only when all of these are available:

- `manual_case.yaml` with external path, expected accelerator, guest port, guest flag path, timeout, and PoC command.
- `asset_manifest.yaml` with kernel/initrd/rootfs file names, sizes, and SHA256 values.
- Static contract result from `validate.sh` or a documented legacy-contract exception.
- Boot JSON summary from `scripts/linux_qemu_manual_check.sh --mode boot`.
- Dynamic flag readback JSON summary from `--mode flag` or `--mode full`.
- PoC evidence with a clear success condition, such as root shell, target file read, or expected exploit output.

`Build_test/linux-qemu-copy-fail-missing-assets/manual_case.yaml` is intentionally a candidate/negative record. It should remain `unsupported` until the missing VM assets and PoC evidence are available.

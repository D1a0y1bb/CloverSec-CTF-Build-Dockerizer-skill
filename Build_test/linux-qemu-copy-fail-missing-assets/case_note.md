# Case Note

- Case ID: `linux-qemu-copy-fail-missing-assets`
- Original source: `/Users/d1a0y1bb/Documents/VulnEnvironment/CVE-2026-31431 Copy Fail Linux Kernel LPE/code`
- Input status: high_risk
- Expected path: manual_review
- Support level: unsupported
- Manual confirmation required: true
- Verification level: manual
- Contract expectation: fail
- Suggested command: `python3 scripts/validate_build_test.py --case linux-qemu-copy-fail-missing-assets`
- Current limits: VM assets are intentionally absent; full boot, guest flag injection, and PoC checks belong to P1.4 manual validation.

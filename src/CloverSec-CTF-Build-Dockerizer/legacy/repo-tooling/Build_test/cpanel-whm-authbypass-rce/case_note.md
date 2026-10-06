# Case Note

- Case ID: `cpanel-whm-authbypass-rce`
- Original source: `/Users/d1a0y1bb/Documents/VulnEnvironment/CVE-2026-41940 watchTowr-vs-cPanel-WHM-AuthBypass-to-RCE/code`
- Input status: mixed
- Expected path: bundle_recipe
- Support level: partial
- Manual confirmation required: true
- Verification level: manual
- Contract expectation: pass
- Suggested command: `python3 scripts/validate_build_test.py --case cpanel-whm-authbypass-rce`
- Current limits: Docker contract is complete, but product routing should still treat cPanel/WHM as recipe-style work rather than linux-qemu. TLS PEM/key material is represented by placeholder files so release guards do not package private key material.

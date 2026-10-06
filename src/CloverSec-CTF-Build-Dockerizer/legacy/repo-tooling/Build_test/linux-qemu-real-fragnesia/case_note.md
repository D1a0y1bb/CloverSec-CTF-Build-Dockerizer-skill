# Case Note

- Case ID: `linux-qemu-real-fragnesia`
- Original source: `/Users/d1a0y1bb/Documents/VulnEnvironment/CVE-2026-46300 Fragnesia Linux Kernel LPE/code`
- Input status: high_risk
- Expected path: manual_review
- Support level: partial
- Manual confirmation required: true
- Verification level: manual
- Contract expectation: external manual validation
- Suggested command: `bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir "/Users/d1a0y1bb/Documents/VulnEnvironment/CVE-2026-46300 Fragnesia Linux Kernel LPE/code"`
- Current limits: VM assets are stored outside the repository. Static validation may still report legacy `challenge.vm` gaps; boot evidence is recorded by the manual script.

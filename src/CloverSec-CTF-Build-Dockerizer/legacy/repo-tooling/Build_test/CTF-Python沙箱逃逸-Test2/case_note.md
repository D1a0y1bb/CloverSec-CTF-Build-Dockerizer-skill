# Case Note

- Case ID: `python-sandbox-existing`
- Original source: `Build_test/CTF-Python沙箱逃逸-Test2` before P1.3
- Input status: clean
- Expected path: direct_render
- Support level: supported
- Manual confirmation required: false
- Verification level: static
- Contract expectation: pass
- Suggested command: `python3 scripts/validate_build_test.py --case python-sandbox-existing`
- Current limits: the nested `src/requirements.txt` is recognized by the audit; Docker build and business solving remain separate checks.

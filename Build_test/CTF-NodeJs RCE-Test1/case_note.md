# Case Note

- Case ID: `node-rce-existing`
- Original source: `Build_test/CTF-NodeJs RCE-Test1` before P1.3
- Input status: clean
- Expected path: direct_render
- Support level: supported
- Manual confirmation required: false
- Verification level: static
- Contract expectation: fail
- Suggested command: `python3 scripts/validate_build_test.py --case node-rce-existing`
- Current limits: historical Dockerfile misses the current `changeflag.sh` delivery contract.

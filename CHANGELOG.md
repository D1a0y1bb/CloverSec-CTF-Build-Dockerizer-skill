# Changelog

All notable changes to this project are documented in this file.

## v1.2.4 - 2026-02-24

### Added

- Added standalone English documentation file: `README.en.md`.
- Added language switch links at the top of both README files.
- Added complete bilingual documentation layout with separate Chinese and English files.

### Changed

- Rewrote `README.md` into an official Simplified Chinese primary document with standardized release-grade structure.
- Updated release guidance to center around `scripts/publish_release.sh` for one-command publishing.

### Security / Repo Hygiene

- Archived `internal/` to a local desktop archive path and removed `internal/` from the working repository.
- Removed legacy local workspace directory and symlink alias, retaining one canonical workspace path.
- Confirmed `SESSION_SUMMARY_v1.2.2.md` is removed from the repository workspace.

### Release

- Bumped version to `v1.2.4`.
- Generated release artifacts as `dist/CloverSec-CTF-Build-Dockerizer-v1.2.4/` and `dist/CloverSec-CTF-Build-Dockerizer-v1.2.4.zip`.
- Published GitHub release `v1.2.4` with downloadable zip asset.

## v1.2.3 - 2026-02-24

### Added

- Added a bilingual README layout: Chinese main documentation + English brief summary.
- Added `CHANGELOG.md` as a stable release-history entry point.
- Added explicit link to GitHub Releases in `README.md`.

### Changed

- Rewrote `README.md` into a formal public-release format:
  - clear scope and non-scope
  - standardized install and usage guidance
  - structured platform constraints and stack matrix
  - concise, repository-facing documentation index

### Notes

- This version focuses on documentation and release presentation.
- Core rendering/validation pipeline behavior remains unchanged.

## v1.2.2 - 2026-02-24

### Added

- Added documentation quality gate script: `scripts/doc_guard.sh`.
- Added auditable phase timeline section in root README.

### Changed

- Integrated `doc_guard.sh` into `scripts/release_build.sh`.
- Strengthened release-time document validation.

### Fixed

- Removed stale references and missing-path document links.
- Unified naming strategy for public documentation.

## v1.2.1 - 2026-02-24

### Changed

- Upgraded `SKILL.md` frontmatter description to better reflect Jeopardy (Web/Pwn/AI) scope.
- Expanded `argument-hint` to cover all 8 supported stacks.

## v1.2.0 - 2026-02-24

### Added

- Completed project rename to `CloverSec-CTF-Build-Dockerizer`.
- Added `pwn` and `ai` stack support (templates/rules/examples/regression).
- Enforced versioned release artifact naming based on root `VERSION`.

### Changed

- Release packaging changed to single-directory zip layout.
- Dist naming and release structure normalized for traceability.

### Notes

- Scope remains Jeopardy-only. AWD/AWDP are out of scope.

#!/usr/bin/env python3
"""Core v3 delivery invariants without Docker or network access."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "CloverSec-CTF-Build-Dockerizer" / "scripts" / "ctfctl.py"
SPEC = importlib.util.spec_from_file_location("ctfctl_v3", MODULE_PATH)
assert SPEC and SPEC.loader
ctfctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ctfctl)


class CtfctlV3Test(unittest.TestCase):
    def write_input(self, root: Path) -> Path:
        project = root / "input"
        (project / "src").mkdir(parents=True)
        (project / "tools").mkdir()
        (project / "src" / "app.py").write_text("print('ready')\n", encoding="utf-8")
        (project / "Dockerfile").write_text(
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY src/ /app/\n"
            "COPY start.sh /start.sh\n"
            "COPY flag /flag\n"
            "EXPOSE 5000\n"
            "CMD [\"/start.sh\"]\n",
            encoding="utf-8",
        )
        (project / "start.sh").write_text("#!/bin/sh\nexec python3 /app/app.py\n", encoding="utf-8")
        (project / "flag").write_text("flag{local}\n", encoding="utf-8")
        (project / "changeflag.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (project / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
        (project / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (project / "tools" / "capture_http.py").write_text("print('tool')\n", encoding="utf-8")
        return project

    def test_clean_scaffold_generates_contract_and_removes_authoring_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctfctl-v3-test-") as temp:
            root = Path(temp)
            project = self.write_input(root)
            output = root / "output"
            result = ctfctl.prepare(project, output, profile="clean")

            self.assertEqual(result["contract"]["flag"]["mode"], "direct_exec")
            self.assertTrue((output / "challenge.yaml").is_file())
            self.assertTrue((output / "src" / "app.py").is_file())
            self.assertTrue((output / ".ctfbuild" / "audit.json").is_file())
            self.assertFalse((output / "changeflag.sh").exists())
            self.assertFalse((output / "docker-compose.yml").exists())
            self.assertFalse((output / "run.sh").exists())
            self.assertFalse((output / "tools").exists())

    def test_audit_reports_advanced_input_and_nested_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctfctl-v3-audit-") as temp:
            project = self.write_input(Path(temp))
            nested = project / "legacy" / "changeflag.sh"
            nested.parent.mkdir()
            nested.write_text("#!/bin/sh\n", encoding="utf-8")
            result = ctfctl.audit(project)

            self.assertTrue(result["advanced_inputs"])
            self.assertGreaterEqual(len(result["helper_paths"]), 2)
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("ADVANCED_INPUT_PRESENT", codes)
            self.assertIn("LEGACY_HELPER_PRESENT", codes)


if __name__ == "__main__":
    unittest.main()

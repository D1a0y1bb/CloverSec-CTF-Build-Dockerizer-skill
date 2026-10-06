#!/usr/bin/env python3
"""Core v3 delivery invariants without Docker or network access."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socket import socket


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
            archive = ctfctl.package(output, root / "challenge.tar.gz")
            self.assertEqual(archive["status"], "passed")

    def test_clean_scaffold_removes_all_helper_references_from_readonly_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctfctl-v3-helper-") as temp:
            root = Path(temp)
            project = self.write_input(root)
            (project / "Dockerfile").write_text(
                "FROM python:3.11-slim\n"
                "COPY src/ /app/\n"
                "COPY changeflag.sh /changeflag.sh\n"
                "COPY flag /flag\n"
                "RUN chmod 555 /start.sh /changeflag.sh && chmod 444 /flag\n"
                "RUN test -f /flag && \\\n"
                "    chmod 555 /start.sh && chmod 555 /changeflag.sh && \\\n"
                "    chmod 444 /flag\n"
                "CMD [\"/start.sh\"]\n",
                encoding="utf-8",
            )
            (project / "start.sh").write_text(
                "#!/bin/sh\n"
                "# long authoring note\n"
                "exec python3 /app/app.py\n",
                encoding="utf-8",
            )
            (project / "Dockerfile").chmod(0o444)
            (project / "start.sh").chmod(0o555)
            output = root / "output"

            result = ctfctl.prepare(project, output, profile="clean")

            self.assertIn("Dockerfile", result["audit"]["migrations"])
            self.assertNotIn("changeflag.sh", (output / "Dockerfile").read_text(encoding="utf-8"))
            self.assertNotIn("chmod 555 &&", (output / "Dockerfile").read_text(encoding="utf-8"))
            self.assertNotIn("changeflag.sh", (output / "start.sh").read_text(encoding="utf-8"))
            self.assertFalse((output / "changeflag.sh").exists())
            self.assertEqual(
                json.loads((output / ".ctfbuild" / "prepare-state.json").read_text(encoding="utf-8"))["status"],
                "ready",
            )

    def test_package_rejects_incomplete_scaffold_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctfctl-v3-package-") as temp:
            root = Path(temp)
            project = root / "delivery"
            (project / ".ctfbuild").mkdir(parents=True)
            (project / ".ctfbuild" / "prepare-state.json").write_text(
                '{"schema_version":"1.0","profile":"clean","status":"running"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "尚未完成 scaffold"):
                ctfctl.package(project, root / "failed.tar.gz")

    def test_attachment_only_keeps_config_and_reports_partial_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctfctl-v3-attachment-") as temp:
            root = Path(temp)
            project = root / "input"
            project.mkdir()
            (project / "challenge.yaml").write_text("category: scenario\n", encoding="utf-8")
            (project / "scenario.yaml").write_text("scenario:\n  services: []\n", encoding="utf-8")
            output = root / "output"

            result = ctfctl.prepare(project, output, profile="clean")
            archive = ctfctl.package(output, root / "scenario.tar.gz")

            self.assertEqual(result["audit"]["delivery_kind"], "attachment-only")
            self.assertTrue((output / "challenge.yaml").is_file())
            self.assertEqual(archive["status"], "partial")
            self.assertEqual(archive["delivery_kind"], "attachment-only")

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

    def test_probe_http_checks_response_text(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                body = b"probe-body"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            passed = ctfctl.probe_http("127.0.0.1", server.server_port, "/", 200, "probe-body")
            failed = ctfctl.probe_http("127.0.0.1", server.server_port, "/", 200, "missing-body")
            self.assertEqual(passed["status_result"], "passed")
            self.assertEqual(failed["status_result"], "failed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_probe_tcp_checks_banner_text(self) -> None:
        listener = socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)

        def serve_once() -> None:
            connection, _ = listener.accept()
            with connection:
                connection.sendall(b"welcome-banner\n")

        thread = threading.Thread(target=serve_once, daemon=True)
        thread.start()
        try:
            result = ctfctl.probe_tcp("127.0.0.1", listener.getsockname()[1], "welcome-banner")
            self.assertEqual(result["status_result"], "passed")
        finally:
            listener.close()
            thread.join(timeout=2)

    def test_network_probe_retries_startup_race(self) -> None:
        attempts = 0

        def probe() -> dict[str, object]:
            nonlocal attempts
            attempts += 1
            return {"status_result": "passed" if attempts == 2 else "failed"}

        result = ctfctl.retry_network_probe(probe, 2)

        self.assertEqual(result["status_result"], "passed")
        self.assertEqual(result["attempts"], 2)


if __name__ == "__main__":
    unittest.main()

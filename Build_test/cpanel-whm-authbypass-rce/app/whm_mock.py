#!/usr/bin/env python3
from __future__ import annotations

import base64
import html
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "0.0.0.0"
PORT = 2087
CERT = "/opt/whm/cert.pem"
KEY = "/opt/whm/key.pem"
VERSION = "11.110.0.89"
APP_NAME = "云盾主机管理系统"
APP_SUBTITLE = "站点与服务管理平台"
PATCHED_MODE = os.environ.get("WHM_PATCHED", "0") == "1"
VALID_USERS = {
    "admin": {"password": "123456", "role": "运营管理员", "hasroot": "0"},
}

SESSION_RAW_DIR = "/var/cpanel/sessions/raw"
SESSION_ROOT_DIR = "/var/cpanel/sessions/root"
CPANEL_LOG_DIR = "/usr/local/cpanel/logs"
ACCESS_LOG = os.path.join(CPANEL_LOG_DIR, "access_log")
ERROR_LOG = os.path.join(CPANEL_LOG_DIR, "error_log")
VERSION_FILE = "/usr/local/cpanel/version"

ACCOUNTS = [
    {"user": "alice", "domain": "alice.example.test", "owner": "root", "theme": "jupiter"},
    {"user": "webmaster", "domain": "portal.example.test", "owner": "admin", "theme": "jupiter"},
]


def now() -> int:
    return int(time.time())


def ensure_layout() -> None:
    for path in (SESSION_RAW_DIR, SESSION_ROOT_DIR, CPANEL_LOG_DIR, "/usr/local/cpanel/Cpanel/Session"):
        os.makedirs(path, exist_ok=True)
    with open(VERSION_FILE, "w", encoding="utf-8") as fh:
        fh.write(VERSION + "\n")
    for path in (ACCESS_LOG, ERROR_LOG):
        open(path, "a", encoding="utf-8").close()


def read_flag() -> str:
    with open("/flag", "r", encoding="utf-8") as fh:
        return fh.read().strip()


def parse_cookie(raw: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for item in raw.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        cookies[key.strip()] = urllib.parse.unquote(value.strip())
    return cookies


def split_session_cookie(value: str) -> tuple[str, str | None]:
    match = re.match(r"^(?P<base>:[A-Za-z0-9_-]+)(?:,(?P<ob>[0-9a-f]{1,64}))?$", value)
    if not match:
        return value.split(",", 1)[0], None
    return match.group("base"), match.group("ob")


def session_name(base: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", base.lstrip(":"))


def session_path(base: str) -> str:
    return os.path.join(SESSION_RAW_DIR, session_name(base))


def root_session_path(token: str) -> str:
    return os.path.join(SESSION_ROOT_DIR, token.strip("/"))


def parse_session_text(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def read_session(base: str) -> dict[str, str]:
    path = session_path(base)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_session_text(fh.read())


def read_session_raw(base: str) -> str:
    path = session_path(base)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def filter_sessiondata(value: object) -> str:
    return str(value).replace("\r", "").replace("\n", "")


def write_session(base: str, data: dict[str, object]) -> None:
    lines = [f"{key}={filter_sessiondata(value)}" for key, value in data.items()]
    with open(session_path(base), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_session_raw(base: str, text: str) -> None:
    with open(session_path(base), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def make_session_base() -> str:
    return ":" + secrets.token_urlsafe(12)


def make_token() -> str:
    return f"/cpsess{secrets.randbelow(10_000_000_000):010d}"


def append_access(client: str, user: str, method: str, path: str, status: int, note: str = "-") -> None:
    stamp = time.strftime("%d/%b/%Y:%H:%M:%S %z")
    line = f'{client} - {user or "-"} [{stamp}] "{method} {path} HTTP/1.1" {status} {note}\n'
    with open(ACCESS_LOG, "a", encoding="utf-8") as fh:
        fh.write(line)


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - {APP_NAME}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172033;
      --muted: #637083;
      --line: #d8dee8;
      --panel: #ffffff;
      --side: #1f2f46;
      --brand: #f47b20;
      --bg: #eef2f7;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }}
    header {{ height: 54px; display: flex; align-items: center; gap: 14px; padding: 0 22px; background: #fff; border-bottom: 1px solid var(--line); }}
    header strong {{ color: var(--brand); font-size: 18px; }}
    .shell {{ display: grid; grid-template-columns: 230px 1fr; min-height: calc(100vh - 54px); }}
    aside {{ background: var(--side); color: #dfe7f2; padding: 18px 0; }}
    aside a {{ display: block; padding: 11px 22px; color: #dfe7f2; text-decoration: none; }}
    aside a:hover {{ background: rgba(255,255,255,.09); }}
    main {{ padding: 26px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 20px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)); gap: 14px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 6px; padding: 14px; background: #fafcff; }}
    .metric b {{ display: block; font-size: 22px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; background: #f7f9fc; }}
    code, pre {{ font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    pre {{ overflow: auto; background: #0f1724; color: #e7edf7; border-radius: 6px; padding: 14px; }}
    input, button {{ font: inherit; padding: 9px 11px; border: 1px solid var(--line); border-radius: 5px; }}
    button {{ background: var(--brand); color: #fff; border-color: var(--brand); cursor: pointer; }}
    .login {{ max-width: 440px; margin: 80px auto; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 760px) {{ .shell {{ grid-template-columns: 1fr; }} aside {{ display: none; }} main {{ padding: 16px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header><strong>{APP_NAME}</strong><span class="muted">{APP_SUBTITLE}</span></header>
  {body}
</body>
</html>"""


def layout(token: str, content: str, session: dict[str, str] | None = None) -> str:
    esc_token = html.escape(token)
    session = session or {}
    root_links = ""
    if session.get("hasroot") == "1":
        root_links = f"""
    <a href="{esc_token}/json-api/terminal">运维终端</a>
    <a href="{esc_token}/session-view">会话记录</a>"""
    return f"""<div class="shell">
  <aside>
    <a href="{esc_token}/">控制台</a>
    <a href="{esc_token}/scripts2/listaccts">站点账户</a>
    <a href="{esc_token}/server-status">服务状态</a>{root_links}
  </aside>
  <main>{content}</main>
</div>"""


class WHMHandler(BaseHTTPRequestHandler):
    server_version = "cpsrvd/11.110.0.89"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()

    def send_bytes(self, code: int, data: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(code)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        append_access(self.client_address[0], self.access_user(), self.command, self.path, int(code))

    def send_text(self, code: int, body: str, headers: dict[str, str] | None = None) -> None:
        self.send_bytes(code, body.encode("utf-8"), "text/plain; charset=utf-8", headers)

    def send_html(self, code: int, body: str, headers: dict[str, str] | None = None) -> None:
        self.send_bytes(code, body.encode("utf-8"), "text/html; charset=utf-8", headers)

    def send_json(self, code: int, obj: object) -> None:
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_bytes(code, data, "application/json")

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        append_access(self.client_address[0], self.access_user(), self.command, self.path, 307, location)

    def canonical_host(self) -> str:
        host = self.headers.get("Host", f"localhost:{PORT}")
        return host.split(":", 1)[0]

    def current_session(self) -> tuple[str, str | None, dict[str, str]]:
        cookies = parse_cookie(self.headers.get("Cookie", ""))
        raw_value = cookies.get("whostmgrsession", "")
        if not raw_value:
            return "", None, {}
        base, obhex = split_session_cookie(raw_value)
        return base, obhex, read_session(base)

    def access_user(self) -> str:
        _, _, session = self.current_session()
        return session.get("user", "-") if session.get("authenticated") == "1" else "-"

    def token_session_from_path(self, path: str) -> tuple[str, dict[str, str]] | None:
        token_match = re.match(r"^(/cpsess\d{10})(?:/|$)", path)
        if not token_match:
            return None
        preview_token = token_match.group(1)
        preview_path = root_session_path(preview_token)
        if not os.path.exists(preview_path):
            return None
        with open(preview_path, "r", encoding="utf-8", errors="replace") as fh:
            preview_session = parse_session_text(fh.read())
        preview_session["authenticated"] = "1"
        preview_session["token"] = preview_token
        return preview_token, preview_session

    def authorized_token(self, path: str) -> tuple[str, dict[str, str]] | None:
        _, _, session = self.current_session()
        token = session.get("token", "")
        if token and session.get("authenticated") == "1" and (path == token or path.startswith(token + "/")):
            return token, session
        token_from_path = self.token_session_from_path(path)
        if token_from_path:
            return token_from_path
        return None

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/openid_connect/cpanelid":
            self.redirect(f"https://{self.canonical_host()}:{PORT}/login/")
            return
        if parsed.path in {"/", "/login/", "/__health"}:
            self.send_text(HTTPStatus.OK, "")
            return
        self.send_text(HTTPStatus.NOT_FOUND, "")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/__health":
            self.send_text(HTTPStatus.OK, "ok\n")
            return

        if path == "/openid_connect/cpanelid":
            self.redirect(f"https://{self.canonical_host()}:{PORT}/login/")
            return

        if path == "/login/":
            self.send_login()
            return

        if path == "/":
            if self.headers.get("Authorization", "").startswith("Basic "):
                self.handle_injection()
                return
            self.send_login()
            return

        if path == "/scripts2/listaccts":
            base, _, session = self.current_session()
            if session:
                session["cache_propagated"] = "1"
                session["updated_at"] = str(now())
                write_session(base, session)
            self.send_text(HTTPStatus.UNAUTHORIZED, "Token denied\nLogin Required\n")
            print(f"[INFO] token_denied propagation fired for {base}")
            return

        auth = self.authorized_token(path)
        if auth is None:
            if re.match(r"^/cpsess\d{10}(?:/|$)", path):
                self.send_session_expired()
                return
            self.send_text(HTTPStatus.UNAUTHORIZED, "Login Required\n")
            return

        token, session = auth
        if path == token:
            self.redirect(token + "/")
            return
        if path == token + "/":
            self.send_dashboard(token, session)
            return
        if path == token + "/scripts2/listaccts":
            self.send_accounts_page(token, session)
            return
        if path == token + "/server-status":
            self.send_status_page(token, session)
            return
        if path == token + "/json-api/listaccts":
            self.send_json(HTTPStatus.OK, {"metadata": {"result": 1}, "data": {"acct": ACCOUNTS}})
            return
        if path == token + "/json-api/version":
            self.send_json(HTTPStatus.OK, {"version": VERSION})
            return
        if path == token + "/json-api/terminal":
            self.handle_terminal(token, parsed.query, session)
            return
        if path == token + "/session-view":
            self.send_session_view(token, session)
            return

        self.send_text(HTTPStatus.NOT_FOUND, "not found\n")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/login/" and parsed.query == "login_only=1":
            self.handle_login_only()
            return
        if parsed.path == "/login/":
            self.handle_browser_login()
            return
        self.send_text(HTTPStatus.NOT_FOUND, "not found\n")

    def send_login(self, error: str = "") -> None:
        error_block = f'<p style="color:#b42318">{html.escape(error)}</p>' if error else ""
        body = page(
            "登录",
            f"""<main class="login">
  <section class="panel">
    <h1>系统登录</h1>
    <p class="muted">登录后可管理站点账户、域名解析和主机服务。</p>
    {error_block}
    <form method="post" action="/login/">
      <p><input name="user" placeholder="用户名" aria-label="用户名" autocomplete="username" style="width:100%"></p>
      <p><input name="pass" type="password" placeholder="密码" aria-label="密码" autocomplete="current-password" style="width:100%"></p>
      <button type="submit">登录</button>
    </form>
  </section>
</main>""",
        )
        self.send_html(HTTPStatus.OK, body)

    def send_session_expired(self) -> None:
        body = page(
            "会话已失效",
            """<main class="login">
  <section class="panel">
    <h1>会话已失效</h1>
    <p class="muted">当前会话令牌已失效，请重新登录。</p>
    <p><a href="/login/"><button type="button">返回登录</button></a></p>
  </section>
</main>""",
        )
        self.send_html(HTTPStatus.OK, body)

    def handle_browser_login(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8", errors="ignore") if length else ""
        params = urllib.parse.parse_qs(raw_body)
        username = (params.get("user") or [""])[0]
        password = (params.get("pass") or [""])[0]
        account = VALID_USERS.get(username)

        if account is None or account.get("password") != password:
            self.send_login("用户名或密码不正确。")
            return

        base = make_session_base()
        obhex = secrets.token_hex(8)
        token = make_token()
        write_session(
            base,
            {
                "created_at": now(),
                "updated_at": now(),
                "remote_ip": self.client_address[0],
                "login_theme": "jupiter",
                "user": username,
                "role": account.get("role", "User"),
                "pass": "filtered",
                "hasroot": account.get("hasroot", "0"),
                "tfa_verified": "1",
                "successful_internal_auth_with_timestamp": str(now() + 3600),
                "authenticated": "1",
                "cache_propagated": "1",
                "token": token,
                "version": VERSION,
            },
        )
        with open(root_session_path(token), "w", encoding="utf-8") as fh:
            fh.write(
                f"user={username}\n"
                f"role={account.get('role', 'User')}\n"
                f"hasroot={account.get('hasroot', '0')}\n"
                f"source_session={session_name(base)}\n"
                f"created_at={now()}\n"
            )

        raw_cookie = urllib.parse.quote(f"{base},{obhex}", safe="")
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Set-Cookie", f"whostmgrsession={raw_cookie}; path=/; HttpOnly; secure")
        self.send_header("Location", token + "/")
        self.send_header("Content-Length", "0")
        self.end_headers()
        append_access(self.client_address[0], username, self.command, self.path, 303, "browser-login")
        print(f"[INFO] browser login accepted for {username}, token={token}")

    def handle_login_only(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8", errors="ignore") if length else ""
        params = urllib.parse.parse_qs(raw_body)

        base = make_session_base()
        obhex = secrets.token_hex(8)
        username = (params.get("user") or ["root"])[0]
        password = (params.get("pass") or ["wrong"])[0]
        write_session(
            base,
            {
                "created_at": now(),
                "updated_at": now(),
                "remote_ip": self.client_address[0],
                "login_theme": "jupiter",
                "user": filter_sessiondata(username),
                "pass": filter_sessiondata(password),
                "hasroot": "0",
                "tfa_verified": "0",
                "successful_internal_auth_with_timestamp": "0",
                "authenticated": "0",
                "cache_propagated": "0",
                "version": VERSION,
            },
        )

        raw_cookie = urllib.parse.quote(f"{base},{obhex}", safe="")
        body = json.dumps({"status": 0, "security_token": None, "message": "login failed"})
        self.send_response(HTTPStatus.OK)
        self.send_header("Set-Cookie", f"whostmgrsession={raw_cookie}; path=/; HttpOnly; secure")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        append_access(self.client_address[0], username, self.command, self.path, 200, "preauth-session")
        self.wfile.write(body.encode("utf-8"))
        print(f"[INFO] issued preauth session {base}, raw_file={session_path(base)}")

    def handle_injection(self) -> None:
        base, obhex, session = self.current_session()
        if not base or not session:
            self.send_text(HTTPStatus.UNAUTHORIZED, "Login Required\n")
            return

        payload = self.decode_basic()
        if ":" in payload:
            basic_user, password = payload.split(":", 1)
        else:
            basic_user, password = payload, ""

        if PATCHED_MODE or obhex:
            safe_pass = "no-ob:" + password.encode("utf-8", errors="replace").hex() if not obhex else password
            session.update(
                {
                    "updated_at": str(now()),
                    "auth_type": "Basic",
                    "user": basic_user,
                    "pass": safe_pass,
                }
            )
            write_session(base, session)
        else:
            raw = (
                f"created_at={session.get('created_at', now())}\n"
                f"updated_at={now()}\n"
                f"remote_ip={self.client_address[0]}\n"
                f"auth_type=Basic\n"
                f"user={filter_sessiondata(basic_user)}\n"
                f"pass={password}\n"
                f"authenticated=0\n"
                f"version={VERSION}\n"
            )
            write_session_raw(base, raw)

        parsed = read_session(base)
        forged = (
            parsed.get("user") == "root"
            and parsed.get("hasroot") == "1"
            and parsed.get("tfa_verified") == "1"
            and parsed.get("successful_internal_auth_with_timestamp", "0").isdigit()
            and int(parsed.get("successful_internal_auth_with_timestamp", "0")) > now()
        )

        if forged:
            token = make_token()
            parsed["authenticated"] = "1"
            parsed["token"] = token
            parsed["updated_at"] = str(now())
            write_session(base, parsed)
            with open(root_session_path(token), "w", encoding="utf-8") as fh:
                fh.write(f"user=root\nhasroot=1\nsource_session={session_name(base)}\ncreated_at={now()}\n")
            self.redirect(token + "/")
            print(f"[INFO] CRLF session forgery accepted for {base}, token={token}")
            return

        print(f"[INFO] Basic auth write did not create a root session for {base}; patched={PATCHED_MODE}")
        self.send_text(HTTPStatus.UNAUTHORIZED, "Login Required\n")

    def decode_basic(self) -> str:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return ""
        try:
            return base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def send_dashboard(self, token: str, session: dict[str, str]) -> None:
        base = session.get("source_session", "") or self.current_session()[0]
        user = session.get("user", "admin")
        role = session.get("role", "系统管理员" if session.get("hasroot") == "1" else "运营管理员")
        root_tools = "可用" if session.get("hasroot") == "1" else "受限"
        session_panel = ""
        if session.get("hasroot") == "1":
            session_panel = f"""
<section class="panel">
  <h2>近期会话数据</h2>
  <pre>{html.escape(read_session_raw(base))}</pre>
</section>"""
        content = f"""<section class="panel">
  <h1>业务控制台</h1>
  <p class="muted">当前用户：<b>{html.escape(user)}</b>。安全令牌：<code>{html.escape(token)}</code></p>
  <div class="grid">
    <div class="metric">站点账户<b>{len(ACCOUNTS)}</b></div>
    <div class="metric">用户角色<b>{html.escape(role)}</b></div>
    <div class="metric">运维功能<b>{html.escape(root_tools)}</b></div>
  </div>
</section>{session_panel}"""
        self.send_html(HTTPStatus.OK, page("控制台", layout(token, content, session)))

    def send_accounts_page(self, token: str, session: dict[str, str]) -> None:
        rows = "\n".join(
            f"<tr><td>{html.escape(a['user'])}</td><td>{html.escape(a['domain'])}</td><td>{html.escape(a['owner'])}</td><td>{html.escape(a['theme'])}</td></tr>"
            for a in ACCOUNTS
        )
        content = f"""<section class="panel">
  <h1>站点账户</h1>
  <table><thead><tr><th>用户</th><th>域名</th><th>负责人</th><th>主题</th></tr></thead><tbody>{rows}</tbody></table>
</section>"""
        self.send_html(HTTPStatus.OK, page("站点账户", layout(token, content, session)))

    def send_status_page(self, token: str, session: dict[str, str]) -> None:
        content = f"""<section class="panel">
  <h1>服务状态</h1>
  <table>
    <tbody>
      <tr><th>cpsrvd</th><td>running</td></tr>
      <tr><th>Apache</th><td>running</td></tr>
      <tr><th>Exim</th><td>running</td></tr>
      <tr><th>DNS</th><td>running</td></tr>
      <tr><th>License</th><td>active</td></tr>
    </tbody>
  </table>
</section>"""
        self.send_html(HTTPStatus.OK, page("服务状态", layout(token, content, session)))

    def handle_terminal(self, token: str, query: str, session: dict[str, str]) -> None:
        if session.get("hasroot") != "1":
            self.send_text(HTTPStatus.FORBIDDEN, "当前账号没有运维终端权限。\n")
            return
        params = urllib.parse.parse_qs(query)
        cmd = (params.get("cmd") or [""])[0].strip()
        if not cmd:
            content = f"""<section class="panel">
  <h1>运维终端</h1>
  <form method="get" action="{html.escape(token)}/json-api/terminal">
    <input type="hidden" name="api.version" value="1">
    <input name="cmd" value="cat /flag" style="width: min(520px, 100%)">
    <button type="submit">Run</button>
  </form>
</section>"""
            self.send_html(HTTPStatus.OK, page("运维终端", layout(token, content, session)))
            return

        if cmd in {"cat /flag", "/bin/cat /flag"}:
            self.send_json(HTTPStatus.OK, {"metadata": {"result": 1}, "data": {"output": read_flag()}})
            return

        self.send_json(
            HTTPStatus.OK,
            {
                "metadata": {"result": 0},
                "error": "当前仅开放验证命令：cat /flag",
            },
        )

    def send_session_view(self, token: str, session: dict[str, str]) -> None:
        if session.get("hasroot") != "1":
            self.send_text(HTTPStatus.FORBIDDEN, "当前账号没有会话记录权限。\n")
            return
        base = session.get("source_session", "") or self.current_session()[0]
        raw = read_session_raw(base) if base else ""
        root_token_file = root_session_path(token)
        root_raw = ""
        if os.path.exists(root_token_file):
            with open(root_token_file, "r", encoding="utf-8", errors="replace") as fh:
                root_raw = fh.read()
            if not base:
                base = parse_session_text(root_raw).get("source_session", "")
                raw = read_session_raw(base)
        content = f"""<section class="panel">
  <h1>会话记录</h1>
  <p class="muted">原始会话路径：<code>{html.escape(session_path(base))}</code></p>
  <pre>{html.escape(raw)}</pre>
  <p class="muted">高权限令牌路径：<code>{html.escape(root_token_file)}</code></p>
  <pre>{html.escape(root_raw)}</pre>
</section>"""
        self.send_html(HTTPStatus.OK, page("会话记录", layout(token, content, session)))


def main() -> int:
    ensure_layout()
    httpd = ThreadingHTTPServer((HOST, PORT), WHMHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT, KEY)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f"[INFO] host management service listening on https://{HOST}:{PORT}")
    print(f"[INFO] Session files: {SESSION_RAW_DIR}")
    print(f"[INFO] Access log: {ACCESS_LOG}")
    print(f"[INFO] Patched mode: {PATCHED_MODE}")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

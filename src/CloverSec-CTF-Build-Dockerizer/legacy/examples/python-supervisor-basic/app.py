from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok:web:5000\n")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), Handler)
    print("[python-supervisor] web listening on 5000", flush=True)
    server.serve_forever()

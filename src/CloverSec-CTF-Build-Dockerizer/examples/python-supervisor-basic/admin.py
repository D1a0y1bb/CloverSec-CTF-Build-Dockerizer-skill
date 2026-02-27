from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok:admin:5001\n")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5001), Handler)
    print("[python-supervisor] admin listening on 5001", flush=True)
    server.serve_forever()

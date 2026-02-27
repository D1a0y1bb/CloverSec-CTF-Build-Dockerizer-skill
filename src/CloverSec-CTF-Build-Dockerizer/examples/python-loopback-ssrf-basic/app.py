from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return "hello from python-loopback-ssrf-basic\n", 200, {"Content-Type": "text/plain; charset=utf-8"}

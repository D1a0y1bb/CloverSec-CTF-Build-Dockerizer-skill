from flask import Flask, jsonify

app = Flask(__name__)

try:
    import transformers  # noqa: F401
    HAS_TRANSFORMERS = True
except Exception:
    HAS_TRANSFORMERS = False


@app.get("/")
def index():
    return jsonify({"ok": True, "stack": "ai-transformers-basic", "transformers": HAS_TRANSFORMERS})

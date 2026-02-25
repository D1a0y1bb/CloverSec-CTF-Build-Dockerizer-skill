from flask import Flask, request, render_template_string

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    value = request.args.get("id", "rdg-python")
    template = "<h1>Hello {{ value | safe }}</h1>"
    return render_template_string(template, value=value)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)

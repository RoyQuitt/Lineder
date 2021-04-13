import os

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "<h1>Index</h1>"


@app.route("/test")
def test():
    return "<h1>success</h1>"


if __name__ == "__main__":
    port = os.environ.get('PORT')
    app.run(ssl_context="adhoc", host="0.0.0.0", port=port)
    app.run()

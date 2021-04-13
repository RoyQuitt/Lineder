from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "<h1>Index</h1>"


@app.route("/test")
def test():
    return "<h1>success</h1>"


if __name__ == "__main__":
    app.run()

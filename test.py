import os

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
app.config['supports_credentials'] = True
cors = CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

@app.route("/")
def index():
    return "<h1>Index</h1>"


@app.route("/test")
def test():
    return "<h1>success</h1>"


if __name__ == "__main__":
    port = os.environ.get('PORT')
    #app.run(ssl_context="adhoc", host="0.0.0.0", port=port)

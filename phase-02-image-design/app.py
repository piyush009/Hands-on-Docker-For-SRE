from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify(
        message="Hello from optimized Docker image!",
        host=socket.gethostname(),
        environment=os.getenv("APP_ENV", "phase2"),
    )


@app.route("/healthz")
def healthz():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)



from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify(
        message="Hello from Dockerized Flask app!",
        host=socket.gethostname(),
        environment=os.getenv("APP_ENV", "local"),
    )


@app.route("/healthz")
def healthz():
    # In real apps you might check DB, cache, dependencies etc.
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # Bind to 0.0.0.0 so it's reachable from the container network/host mapping
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)



"""
Flask application for Bagel Shop.

This is a minimal API for health checks and future extensions.
Order processing is handled by scheduled workers (main_scripts.py, sub_scripts.py).
"""
import os
from flask import Flask, jsonify

from src.utils.logger import setup_logger


# Setup logging
setup_logger(log_file="logs/flask.log")

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/", methods=["GET"])
def index():
    """Root endpoint."""
    return jsonify({
        "service": "Bagel Shop API",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
        }
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

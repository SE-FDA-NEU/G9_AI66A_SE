"""Flask web app - Sports Venue Booking System.

Run from the repository root:  python src/app.py
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()


def create_app(database=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only")
    app.config["DATABASE"] = database

    @app.route("/health")
    def health():
        # Used by docs/SETUP.md to check the app is up.
        return jsonify(status="ok")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)

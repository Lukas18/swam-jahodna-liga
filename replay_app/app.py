"""Local Flask server for a standalone uDisc leaderboard replay."""
from pathlib import Path
import os
from zipfile import BadZipFile

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

if __package__:
    from .parser import load_layouts, parse_workbook
else:
    # Also support running this file directly from an IDE or the command line.
    from parser import load_layouts, parse_workbook


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
DEFAULT_LAYOUTS = Path(__file__).resolve().parents[1] / "data" / "league.json"


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/workbook")
def workbook():
    upload = request.files.get("file")
    if upload is None or not upload.filename.lower().endswith(".xlsx"):
        return jsonify(error="Choose a uDisc .xlsx workbook"), 400
    try:
        parsed = parse_workbook(upload.read())
        layouts_path = os.environ.get("REPLAY_LAYOUTS_PATH", str(DEFAULT_LAYOUTS))
        parsed["layouts"] = load_layouts(layouts_path)
        return jsonify(parsed)
    except BadZipFile:
        return jsonify(error="Could not read workbook. Choose a valid, uncorrupted .xlsx file."), 400
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return jsonify(error="Workbook is too large (8 MB maximum)"), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5055")), debug=False)

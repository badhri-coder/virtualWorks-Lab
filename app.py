"""
User Profile Card Generator - Backend
--------------------------------------
A minimal Flask backend that:
  1. Serves a single-page frontend with a profile form
  2. Accepts POST /api/profile with name, bio, image_url
  3. "Processes" the data on the backend:
       - trims/validates input
       - generates initials (for a fallback avatar)
       - shortens an overly long bio
       - builds a join-date style timestamp
  4. Returns a JSON "profile card" object which the frontend renders
  5. Optionally stores the last N generated profiles in SQLite so a
     history list can be shown (demonstrates storage + retrieval too)

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify, render_template
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

DB_NAME = "profiles.db"
MAX_BIO_LENGTH = 150


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bio TEXT NOT NULL,
            image_url TEXT,
            initials TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Processing helpers
# ---------------------------------------------------------------------
def get_initials(name):
    """Turn 'Jane Ann Doe' into 'JD' (first + last word initials)."""
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def is_valid_url(url):
    """Very small sanity check for an image URL — not exhaustive validation."""
    if not url:
        return True  # image is optional
    pattern = re.compile(r"^https?://.+\.(png|jpg|jpeg|gif|webp)(\?.*)?$", re.IGNORECASE)
    return bool(pattern.match(url.strip()))


def format_bio(bio):
    """Trim whitespace and truncate overly long bios with an ellipsis."""
    bio = bio.strip()
    if len(bio) > MAX_BIO_LENGTH:
        return bio[:MAX_BIO_LENGTH].rstrip() + "..."
    return bio


# ---------------------------------------------------------------------
# Routes - Frontend
# ---------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------------------
# Routes - API
# ---------------------------------------------------------------------
@app.route("/api/profile", methods=["POST"])
def create_profile():
    """Receive form data, process it, store it, and return the card data."""
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data received"}), 400

    name = (data.get("name") or "").strip()
    bio = (data.get("bio") or "").strip()
    image_url = (data.get("image_url") or "").strip()

    # ---- validation ----
    errors = {}
    if not name:
        errors["name"] = "Name is required."
    elif len(name) > 60:
        errors["name"] = "Name must be 60 characters or fewer."

    if not bio:
        errors["bio"] = "Bio is required."

    if image_url and not is_valid_url(image_url):
        errors["image_url"] = "Image URL must be a valid http(s) link to an image (png/jpg/jpeg/gif/webp)."

    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400

    # ---- processing ----
    processed_bio = format_bio(bio)
    initials = get_initials(name)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- storage ----
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO profiles (name, bio, image_url, initials, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, processed_bio, image_url, initials, created_at),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    profile_card = {
        "id": new_id,
        "name": name,
        "bio": processed_bio,
        "image_url": image_url,
        "initials": initials,
        "created_at": created_at,
    }
    return jsonify(profile_card), 201


@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    """Return previously generated profiles, most recent first."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM profiles ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Profile deleted"}), 200


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

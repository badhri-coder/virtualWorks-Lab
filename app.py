"""
Quick Note Application - Backend
---------------------------------
A minimal Flask backend that:
  1. Serves a single-page frontend (index.html)
  2. Accepts new notes via POST /api/notes
  3. Stores notes in a SQLite database (notes.db)
  4. Returns all saved notes via GET /api/notes
  5. Allows deleting a note via DELETE /api/notes/<id>

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify, render_template
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_NAME = "notes.db"


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create the notes table if it doesn't already exist."""
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Routes - Frontend
# ---------------------------------------------------------------------
@app.route("/")
def home():
    """Serve the single-page frontend."""
    return render_template("index.html")


# ---------------------------------------------------------------------
# Routes - API
# ---------------------------------------------------------------------
@app.route("/api/notes", methods=["GET"])
def get_notes():
    """Return all notes, most recent first."""
    conn = get_db_connection()
    notes = conn.execute(
        "SELECT * FROM notes ORDER BY id DESC"
    ).fetchall()
    conn.close()

    notes_list = [dict(note) for note in notes]
    return jsonify(notes_list), 200


@app.route("/api/notes", methods=["POST"])
def add_note():
    """Save a new note sent from the frontend."""
    data = request.get_json(silent=True)

    if not data or "content" not in data or not data["content"].strip():
        return jsonify({"error": "Note content cannot be empty"}), 400

    content = data["content"].strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO notes (content, created_at) VALUES (?, ?)",
        (content, created_at),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    new_note = {"id": new_id, "content": content, "created_at": created_at}
    return jsonify(new_note), 201


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    """Delete a note by id."""
    conn = get_db_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Note deleted"}), 200


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

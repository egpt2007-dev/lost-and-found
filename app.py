from matching import find_matches
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_NAME = "lost_and_found.db"

def get_db_connection():
    """Helper function to open a connection to SQLite."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name like dictionary keys
    return conn

@app.route('/')
def home():
    return "It works! Lost & Found backend is running."

# Route to render form (GET) and receive form submission (POST)
@app.route('/post', methods=['GET', 'POST'])
def post_item():
    if request.method == 'POST':
        item_type = request.form['type']
        description = request.form['description']
        location = request.form['location']
        date = request.form['date']
        contact_info = request.form['contact_info']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO items (type, description, location, date, contact_info, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_type, description, location, date, contact_info, 'active')
        )
        conn.commit()
        new_item_id = cursor.lastrowid
        conn.close()

        matches = find_matches(description, item_type)

        return render_template(
            'post_success.html',
            matches=matches,
            lost_item_id=new_item_id,
            item_type=item_type
        )

    return render_template('post_item.html')


@app.route('/items')
def browse_items():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return render_template('browse_items.html', items=items)


@app.route('/claim/<int:found_item_id>/<int:lost_item_id>')
def submit_claim(found_item_id, lost_item_id):
    conn = get_db_connection()

    # Get the similarity score by re-running the match
    lost_item = conn.execute("SELECT * FROM items WHERE id = ?", (lost_item_id,)).fetchone()
    matches = find_matches(lost_item['description'], lost_item['type'])
    score = next((s for item, s in matches if item['id'] == found_item_id), 0)

    conn.execute(
        "INSERT INTO claims (found_item_id, lost_item_id, similarity_score, status) VALUES (?, ?, ?, ?)",
        (found_item_id, lost_item_id, score, 'pending')
    )
    conn.commit()
    conn.close()

    return "Claim submitted! The finder will review it and confirm if it's a match."


@app.route('/review/<int:found_item_id>')
def review_claims(found_item_id):
    conn = get_db_connection()
    found_item = conn.execute(
        "SELECT * FROM items WHERE id = ?", (found_item_id,)
    ).fetchone()
    claims = conn.execute(
        """
        SELECT claims.*, items.description AS lost_description,
               items.location AS lost_location, items.date AS lost_date
        FROM claims
        JOIN items ON claims.lost_item_id = items.id
        WHERE claims.found_item_id = ? AND claims.status = 'pending'
        ORDER BY claims.similarity_score DESC
        """,
        (found_item_id,)
    ).fetchall()
    conn.close()

    return render_template('review_claims.html', found_item=found_item, claims=claims)


@app.route('/claim/<int:claim_id>/confirm', methods=['POST'])
def confirm_claim(claim_id):
    conn = get_db_connection()
    claim = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()

    # Confirm this claim
    conn.execute("UPDATE claims SET status = 'confirmed' WHERE id = ?", (claim_id,))

    # Reject all other pending claims on the same found item
    conn.execute(
        "UPDATE claims SET status = 'rejected' WHERE found_item_id = ? AND id != ?",
        (claim['found_item_id'], claim_id)
    )

    # Mark the found item as claimed
    conn.execute("UPDATE items SET status = 'claimed' WHERE id = ?", (claim['found_item_id'],))

    # Mark ONLY the confirmed claimant's lost item as resolved
    conn.execute("UPDATE items SET status = 'resolved' WHERE id = ?", (claim['lost_item_id'],))

    conn.commit()

    # Fetch both contact details to show
    found_item = conn.execute("SELECT * FROM items WHERE id = ?", (claim['found_item_id'],)).fetchone()
    lost_item = conn.execute("SELECT * FROM items WHERE id = ?", (claim['lost_item_id'],)).fetchone()
    conn.close()

    return render_template('claim_confirmed.html', found_item=found_item, lost_item=lost_item)


@app.route('/claim/<int:claim_id>/reject', methods=['POST'])
def reject_claim(claim_id):
    conn = get_db_connection()
    claim = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    conn.execute("UPDATE claims SET status = 'rejected' WHERE id = ?", (claim_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('review_claims', found_item_id=claim['found_item_id']))

@app.route('/api/items', methods=['GET'])
def api_get_items():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return {"items": [dict(row) for row in items]}


@app.route('/api/items', methods=['POST'])
def api_post_item():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (type, description, location, date, contact_info, status) VALUES (?, ?, ?, ?, ?, ?)",
        (data['type'], data['description'], data['location'], data['date'], data['contact_info'], 'active')
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    matches = find_matches(data['description'], data['type'])
    return {
        "id": new_id,
        "matches": [
            {"id": item['id'], "description": item['description'], "location": item['location'], "date": item['date'], "score": score}
            for item, score in matches
        ]
    }


@app.route('/api/claims', methods=['POST'])
def api_submit_claim():
    data = request.get_json()
    found_item_id = data['found_item_id']
    lost_item_id = data['lost_item_id']

    conn = get_db_connection()
    lost_item = conn.execute("SELECT * FROM items WHERE id = ?", (lost_item_id,)).fetchone()
    matches = find_matches(lost_item['description'], lost_item['type'])
    score = next((s for item, s in matches if item['id'] == found_item_id), 0)

    conn.execute(
        "INSERT INTO claims (found_item_id, lost_item_id, similarity_score, status) VALUES (?, ?, ?, ?)",
        (found_item_id, lost_item_id, score, 'pending')
    )
    conn.commit()
    conn.close()
    return {"message": "Claim submitted"}


@app.route('/api/items/<int:found_item_id>/claims', methods=['GET'])
def api_get_claims(found_item_id):
    conn = get_db_connection()
    found_item = conn.execute("SELECT * FROM items WHERE id = ?", (found_item_id,)).fetchone()
    claims = conn.execute(
        """
        SELECT claims.*, items.description AS lost_description,
               items.location AS lost_location, items.date AS lost_date
        FROM claims JOIN items ON claims.lost_item_id = items.id
        WHERE claims.found_item_id = ? AND claims.status = 'pending'
        ORDER BY claims.similarity_score DESC
        """,
        (found_item_id,)
    ).fetchall()
    conn.close()
    return {
        "found_item": dict(found_item) if found_item else None,
        "claims": [dict(c) for c in claims]
    }


@app.route('/api/claims/<int:claim_id>/confirm', methods=['POST'])
def api_confirm_claim(claim_id):
    conn = get_db_connection()
    claim = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()

    conn.execute("UPDATE claims SET status = 'confirmed' WHERE id = ?", (claim_id,))
    conn.execute("UPDATE claims SET status = 'rejected' WHERE found_item_id = ? AND id != ?", (claim['found_item_id'], claim_id))
    conn.execute("UPDATE items SET status = 'claimed' WHERE id = ?", (claim['found_item_id'],))
    conn.execute("UPDATE items SET status = 'resolved' WHERE id = ?", (claim['lost_item_id'],))
    conn.commit()

    found_item = conn.execute("SELECT * FROM items WHERE id = ?", (claim['found_item_id'],)).fetchone()
    lost_item = conn.execute("SELECT * FROM items WHERE id = ?", (claim['lost_item_id'],)).fetchone()
    conn.close()

    return {"found_item": dict(found_item), "lost_item": dict(lost_item)}


@app.route('/api/claims/<int:claim_id>/reject', methods=['POST'])
def api_reject_claim(claim_id):
    conn = get_db_connection()
    conn.execute("UPDATE claims SET status = 'rejected' WHERE id = ?", (claim_id,))
    conn.commit()
    conn.close()
    return {"message": "Claim rejected"}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
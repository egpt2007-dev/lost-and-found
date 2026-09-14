from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3

DB_NAME = "lost_and_found.db"
SIMILARITY_THRESHOLD = 0.3  # only show matches scoring above this

def find_matches(new_description, new_type):
    """
    Given a newly posted item's description and type ('lost' or 'found'),
    find similar items of the OPPOSITE type already in the database.
    Returns a list of (item_row, similarity_score) tuples, sorted best-first.
    """
    opposite_type = 'found' if new_type == 'lost' else 'lost'

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    candidates = conn.execute(
        "SELECT * FROM items WHERE type = ? AND status = 'active'",
        (opposite_type,)
    ).fetchall()
    conn.close()

    if not candidates:
        return []  # nothing to compare against yet

    # Build a list of all descriptions: the new one first, then every candidate
    descriptions = [new_description] + [c['description'] for c in candidates]

    # Convert descriptions into TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(descriptions)

    # Compare the new description (row 0) against every candidate (rows 1+)
    similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # Pair each candidate with its score, keep only ones above the threshold
    matches = [
        (candidates[i], similarity_scores[i])
        for i in range(len(candidates))
        if similarity_scores[i] >= SIMILARITY_THRESHOLD
    ]

    # Sort best matches first
    matches.sort(key=lambda pair: pair[1], reverse=True)
    return matches


# Quick standalone test - run this file directly to check the logic works
if __name__ == "__main__":
    # Hardcoded fake data to sanity-check matching without touching the real app
    test_conn = sqlite3.connect(DB_NAME)
    test_conn.execute(
        "INSERT INTO items (type, description, location, date, contact_info, status) VALUES (?, ?, ?, ?, ?, ?)",
        ('found', 'Black bag found near the library entrance', 'Library', '2026-08-27', '9999999999', 'active')
    )
    test_conn.commit()
    test_conn.close()

    results = find_matches("black backpack near the library", "lost")
    for item, score in results:
        print(f"Match: {item['description']} (score: {score:.2f})")
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    date TEXT NOT NULL,
    contact_info TEXT NOT NULL,
    photo_path TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    found_item_id INTEGER NOT NULL,
    lost_item_id INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (found_item_id) REFERENCES items(id),
    FOREIGN KEY (lost_item_id) REFERENCES items(id)
);
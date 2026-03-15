from flask import Flask, jsonify, request, session, redirect, url_for, render_template_string
from flask_cors import CORS
from pathlib import Path
import os, json, sqlite3, hashlib, re, unicodedata
from datetime import datetime
from functools import wraps

BASE_DIR  = Path(os.path.abspath(__file__)).parent
HTML_PATH = BASE_DIR / "index.html"
DB_PATH   = BASE_DIR / "mushayara.db"

app = Flask(__name__)
app.secret_key = "dm_secret_mushayara_2024_nadeem"
CORS(app)

# ── DB HELPER ────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ── SLUG HELPER ──────────────────────────
def make_slug(title, sid):
    """Generate a clean URL slug from shaayari title + id."""
    if not title:
        return str(sid)
    # Normalize unicode → closest ASCII
    normalized = unicodedata.normalize('NFKD', title)
    ascii_title = normalized.encode('ascii', 'ignore').decode('ascii')
    ascii_title = ascii_title.lower()
    ascii_title = re.sub(r'[^a-z0-9\s-]', '', ascii_title)
    ascii_title = re.sub(r'[\s_-]+', '-', ascii_title).strip('-')
    # Append id so every slug is unique and we can always recover the id
    if ascii_title:
        return f"{ascii_title}-{sid}"
    # Urdu / non-ASCII title: just use the id
    return str(sid)

def sid_from_slug(slug):
    """Extract shaayari id from slug. Slug format: <words>-<id> or just <id>."""
    parts = slug.split('-')
    # Try parts from the end until we find one that's a valid id
    for part in reversed(parts):
        if part:  # could be alphanumeric id like "ishq_teri" or numeric
            return part
    return slug

# ── AUTH ─────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

# ── PUBLIC ROUTES ────────────────────────
@app.route("/")
def index():
    if HTML_PATH.exists():
        return HTML_PATH.read_text(encoding="utf-8")
    return "<h2>index.html not found</h2>", 404

# ── INDIVIDUAL SHAAYARI PAGE ─────────────
@app.route("/shaayari/<slug>")
def shaayari_page(slug):
    """
    Shareable individual shaayari URL.
    Serves index.html with:
      - Open Graph meta tags injected (WhatsApp / Twitter previews)
      - window.__DIRECT_SHAAYARI_ID__ so JS auto-opens the modal
    """
    sid = sid_from_slug(slug)

    db = get_db()
    row = db.execute(
        "SELECT * FROM shaayaris WHERE id = ? AND status = 'published'", (sid,)
    ).fetchone()
    db.close()

    if not row:
        # graceful fallback — load homepage, JS will just show nothing
        if HTML_PATH.exists():
            return HTML_PATH.read_text(encoding="utf-8"), 404
        return "Shaayari not found", 404

    if not HTML_PATH.exists():
        return "index.html not found", 404

    html = HTML_PATH.read_text(encoding="utf-8")

    title        = (row["title"] or "Shaayari").replace('"', '&quot;')
    body_preview = " ".join((row["body"] or "").split())[:160].replace('"', '&quot;')
    site_url     = "https://nadeemmemon.pythonanywhere.com"
    canonical    = f"{site_url}/shaayari/{slug}"

    og_tags = f"""
    <meta property="og:type"        content="article" />
    <meta property="og:title"       content="{title} — Digital Mushayara" />
    <meta property="og:description" content="{body_preview}..." />
    <meta property="og:url"         content="{canonical}" />
    <meta property="og:site_name"   content="Digital Mushayara" />
    <meta name="twitter:card"       content="summary" />
    <meta name="twitter:title"      content="{title} — Digital Mushayara" />
    <meta name="twitter:description" content="{body_preview}..." />
    <link rel="canonical"           href="{canonical}" />
    <script>window.__DIRECT_SHAAYARI_ID__ = {json.dumps(str(row["id"]))};</script>"""

    html = html.replace("</head>", og_tags + "\n</head>", 1)
    return html

# ── SLUG API ─────────────────────────────
@app.route("/api/shaayari/<sid>/slug")
def get_shaayari_slug(sid):
    db  = get_db()
    row = db.execute("SELECT id, title FROM shaayaris WHERE id = ?", (sid,)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    slug = make_slug(row["title"], row["id"])
    return jsonify({
        "slug": slug,
        "url":  f"/shaayari/{slug}",
        "full": f"https://nadeemmemon.pythonanywhere.com/shaayari/{slug}"
    })

# ── ALL SHAAYARIS ────────────────────────
@app.route("/api/shaayaris")
def get_all():
    db = get_db()
    rows = db.execute("""
        SELECT s.id, s.title, s.body, s.tags, s.created_at,
               COUNT(DISTINCT r.id) as reaction_count,
               COUNT(DISTINCT c.id) as comment_count
        FROM shaayaris s
        LEFT JOIN reactions r ON r.shaayari_id = s.id
        LEFT JOIN comments c ON c.shaayari_id = s.id
        WHERE s.status = 'published'
        GROUP BY s.id
        ORDER BY s.title
    """).fetchall()
    db.close()

    result = []
    for row in rows:
        db2  = get_db()
        rxns = db2.execute("""
            SELECT reaction, COUNT(*) as cnt
            FROM reactions WHERE shaayari_id = ?
            GROUP BY reaction
        """, (row["id"],)).fetchall()
        db2.close()
        reactions = {r["reaction"]: r["cnt"] for r in rxns}
        result.append({
            "id":        row["id"],
            "title":     row["title"],
            "body":      row["body"],
            "tags":      json.loads(row["tags"] or "[]"),
            "reactions": reactions,
        })
    return jsonify(result)

# ── REACT ────────────────────────────────
@app.route("/api/react", methods=["POST"])
def react():
    data = request.json or {}
    sid, rkey = data.get("id"), data.get("emoji")
    if not sid or not rkey:
        return jsonify({"error": "missing"}), 400

    db  = get_db()
    row = db.execute("SELECT title FROM shaayaris WHERE id = ?", (sid,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "not found"}), 404

    db.execute("INSERT INTO reactions (shaayari_id, reaction) VALUES (?, ?)", (sid, rkey))

    reaction_labels = {
        "waah":    "Waah Waah 👏",
        "khoob":   "Bahut Khoob 🌹",
        "kyabaat": "Kya Baat Hai ✨",
        "dil":     "Dil Ko Chua 💙",
        "aah":     "Aah! 😮"
    }
    db.execute("""
        INSERT INTO notifications (type, shaayari_id, shaayari_title, content)
        VALUES ('reaction', ?, ?, ?)
    """, (sid, row["title"], reaction_labels.get(rkey, rkey)))
    db.commit()

    rxns = db.execute("""
        SELECT reaction, COUNT(*) as cnt FROM reactions
        WHERE shaayari_id = ? GROUP BY reaction
    """, (sid,)).fetchall()
    db.close()

    reactions = {r["reaction"]: r["cnt"] for r in rxns}
    return jsonify({"ok": True, "reactions": reactions})

# ── COMMENT ──────────────────────────────
@app.route("/api/comment", methods=["POST"])
def add_comment():
    data = request.json or {}
    sid  = data.get("id")
    name = (data.get("name") or "Ek Musafir").strip() or "Ek Musafir"
    text = (data.get("text") or "").strip()
    if not sid or not text:
        return jsonify({"error": "missing"}), 400

    db  = get_db()
    row = db.execute("SELECT title FROM shaayaris WHERE id = ?", (sid,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "not found"}), 404

    db.execute(
        "INSERT INTO comments (shaayari_id, name, text) VALUES (?, ?, ?)",
        (sid, name, text)
    )
    # ✅ Notification insert (was missing before — this is the comment bug fix)
    db.execute("""
        INSERT INTO notifications (type, shaayari_id, shaayari_title, content)
        VALUES ('comment', ?, ?, ?)
    """, (sid, row["title"], f"{name}: {text[:80]}"))
    db.commit()

    comments = db.execute("""
        SELECT name, text, created_at FROM comments
        WHERE shaayari_id = ? ORDER BY created_at ASC
    """, (sid,)).fetchall()
    db.close()

    return jsonify({"ok": True, "comments": [dict(c) for c in comments]})

# ── GET COMMENTS ─────────────────────────
@app.route("/api/comments/<sid>")
def get_comments(sid):
    db = get_db()
    comments = db.execute("""
        SELECT name, text, created_at FROM comments
        WHERE shaayari_id = ? ORDER BY created_at ASC
    """, (sid,)).fetchall()
    db.close()
    return jsonify([dict(c) for c in comments])

@app.route("/api/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM shaayaris WHERE status='published'").fetchone()[0]
    db.close()
    return jsonify({"total": total})

# ── ADMIN LOGIN ──────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        db = get_db()
        admin = db.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, hash_password(password))
        ).fetchone()
        db.close()
        if admin:
            session["admin"] = True
            return redirect("/admin")
        error = "Invalid credentials"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

# ── ADMIN PANEL ──────────────────────────
@app.route("/admin")
@login_required
def admin_panel():
    admin_html = BASE_DIR / "admin.html"
    if admin_html.exists():
        return admin_html.read_text(encoding="utf-8")
    return "<h2>admin.html not found</h2>", 404

# ── ADMIN API ────────────────────────────
@app.route("/admin/api/notifications")
@login_required
def get_notifications():
    db = get_db()
    notifs = db.execute("""
        SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50
    """).fetchall()
    unread = db.execute(
        "SELECT COUNT(*) FROM notifications WHERE is_read=0"
    ).fetchone()[0]
    db.close()
    return jsonify({"notifications": [dict(n) for n in notifs], "unread": unread})

@app.route("/admin/api/notifications/read", methods=["POST"])
@login_required
def mark_read():
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1")
    db.commit()
    db.close()
    return jsonify({"ok": True})

@app.route("/admin/api/shaayaris")
@login_required
def admin_shaayaris():
    db = get_db()
    rows = db.execute("""
        SELECT s.*, COUNT(DISTINCT r.id) as reactions,
               COUNT(DISTINCT c.id) as comments
        FROM shaayaris s
        LEFT JOIN reactions r ON r.shaayari_id = s.id
        LEFT JOIN comments c ON c.shaayari_id = s.id
        GROUP BY s.id ORDER BY s.created_at DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/api/shaayari/<sid>")
@login_required
def admin_get_shaayari(sid):
    db  = get_db()
    row = db.execute("SELECT * FROM shaayaris WHERE id=?", (sid,)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))

@app.route("/admin/api/shaayari", methods=["POST"])
@login_required
def admin_add_shaayari():
    data   = request.json or {}
    title  = data.get("title", "").strip()
    body   = data.get("body",  "").strip()
    tags   = data.get("tags",  [])
    status = data.get("status", "published")
    if not title or not body:
        return jsonify({"error": "title and body required"}), 400

    sid = title.lower().replace(" ", "_")[:50]
    db  = get_db()
    existing = db.execute("SELECT id FROM shaayaris WHERE id=?", (sid,)).fetchone()
    if existing:
        sid = sid + "_" + datetime.now().strftime("%H%M%S")

    db.execute(
        "INSERT INTO shaayaris (id, title, body, tags, status) VALUES (?, ?, ?, ?, ?)",
        (sid, title, body, json.dumps(tags), status)
    )
    db.commit()
    db.close()
    return jsonify({"ok": True, "id": sid})

@app.route("/admin/api/shaayari/<sid>", methods=["PUT"])
@login_required
def admin_edit_shaayari(sid):
    data   = request.json or {}
    title  = data.get("title", "").strip()
    body   = data.get("body",  "").strip()
    tags   = data.get("tags",  [])
    status = data.get("status", "published")
    if not title or not body:
        return jsonify({"error": "missing"}), 400

    db = get_db()
    db.execute("""
        UPDATE shaayaris SET title=?, body=?, tags=?, status=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (title, body, json.dumps(tags), status, sid))
    db.commit()
    db.close()
    return jsonify({"ok": True})

@app.route("/admin/api/shaayari/<sid>", methods=["DELETE"])
@login_required
def admin_delete_shaayari(sid):
    db = get_db()
    db.execute("DELETE FROM shaayaris WHERE id=?", (sid,))
    db.commit()
    db.close()
    return jsonify({"ok": True})

@app.route("/admin/api/comments")
@login_required
def admin_comments():
    db = get_db()
    comments = db.execute("""
        SELECT c.*, s.title as shaayari_title
        FROM comments c JOIN shaayaris s ON s.id = c.shaayari_id
        ORDER BY c.created_at DESC LIMIT 50
    """).fetchall()
    db.close()
    return jsonify([dict(c) for c in comments])

@app.route("/admin/api/comment/<int:cid>", methods=["DELETE"])
@login_required
def admin_delete_comment(cid):
    db = get_db()
    db.execute("DELETE FROM comments WHERE id=?", (cid,))
    db.commit()
    db.close()
    return jsonify({"ok": True})

# ── LOGIN PAGE HTML ──────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Digital Mushayara — Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  min-height:100vh;
  background: linear-gradient(145deg, #2a0808 0%, #6b1515 50%, #3d0c0c 100%);
  display:flex; align-items:center; justify-content:center;
  font-family:'Cormorant Garamond',serif;
}
.card {
  background:#fdf6ec; border-radius:24px;
  padding:48px 40px; width:360px;
  box-shadow:0 32px 80px rgba(0,0,0,0.4); text-align:center;
}
.moon { font-size:40px; margin-bottom:12px; display:block; }
h1 { font-family:'Cinzel',serif; font-size:18px; color:#3d0c0c; margin-bottom:4px; letter-spacing:1px; }
.sub { font-size:13px; color:#999; font-style:italic; margin-bottom:32px; }
input {
  width:100%; padding:12px 16px; border:1.5px solid #e8d5b0;
  border-radius:10px; font-family:'Cormorant Garamond',serif;
  font-size:16px; color:#3d0c0c; background:white; outline:none;
  margin-bottom:12px; transition:border-color 0.2s;
}
input:focus { border-color:#c9a84c; }
button {
  width:100%; padding:14px; background:#7b1c1c; color:#fdf6ec;
  border:none; border-radius:10px; font-family:'Cinzel',serif;
  font-size:14px; letter-spacing:1px; cursor:pointer; transition:background 0.2s;
}
button:hover { background:#3d0c0c; }
.error { color:#c0392b; font-size:13px; margin-bottom:16px; font-style:italic; }
</style>
</head>
<body>
<div class="card">
  <span class="moon">🌙</span>
  <h1>Digital Mushayara</h1>
  <p class="sub">Admin Panel</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="text"     name="username" placeholder="Username" required />
    <input type="password" name="password" placeholder="Password" required />
    <button type="submit">Enter</button>
  </form>
</div>
</body>
</html>"""

if __name__ == "__main__":
    print(f"\n  🌙 Digital Mushayara v2")
    print(f"  DB: {DB_PATH}")
    print(f"  Open: http://localhost:5000\n")
    app.run(port=5000, debug=False)
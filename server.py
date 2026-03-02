from flask import Flask, jsonify, request
from pathlib import Path
from flask_cors import CORS
import os, json
from datetime import datetime

BASE_DIR    = Path(os.path.abspath(__file__)).parent
HTML_PATH   = BASE_DIR / "index.html"
JSON_PATH   = BASE_DIR / "shaayaris.json"
BACKUP_ROOT = Path.home() / "Documents" / "Shaayari_Backups"
reactions   = {}
comments    = {}

app = Flask(__name__)
CORS(app)

def get_shaayari_folder():
    if not BACKUP_ROOT.exists():
        return None
    folders = sorted([f for f in BACKUP_ROOT.iterdir() if f.is_dir()], reverse=True)
    for folder in folders:
        p = folder / "Shaayari"
        if p.exists():
            return p
    return None

def parse_txt(filepath):
    text = None
    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
        try:
            text = Path(filepath).read_text(encoding=enc).strip()
            break
        except:
            continue
    if not text:
        return None
    title = Path(filepath).stem.replace("_", " ").strip()
    body  = text
    t     = text.lower()
    tags  = []
    if any(w in t for w in ["love","dil","ishq","mohabbat","pyar","heart"]): tags.append("Love")
    if any(w in t for w in ["sad","dard","pain","aansu","tears","tanhai","gham"]): tags.append("Sad")
    if any(w in t for w in ["sufi","ruh","soul","khuda","allah","ilahi"]): tags.append("Sufi")
    if any(w in t for w in ["waqt","time","zindagi","life","duniya","soch"]): tags.append("Philosophy")
    if any(w in t for w in ["baarish","rain","chaand","moon","phool","darya"]): tags.append("Nature")
    if not tags: tags.append("Nazm")
    return {"id": Path(filepath).stem, "title": title, "body": body, "tags": tags[:2]}

def load_all():
    if JSON_PATH.exists():
        print("  Loading from shaayaris.json")
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        print(f"  Loaded {len(data)} shaayaris")
        return data
    folder = get_shaayari_folder()
    if not folder:
        return []
    files = [f for f in folder.glob("*.txt") if not f.name.startswith("_")]
    data  = [s for f in sorted(files) if (s := parse_txt(f)) is not None]
    print(f"  Loaded {len(data)} shaayaris from txt")
    return data

ALL_SHAAYARIS = load_all()

@app.route("/")
def index():
    if HTML_PATH.exists():
        return HTML_PATH.read_text(encoding="utf-8")
    return "<h2>index.html not found</h2>", 404

@app.route("/api/shaayaris")
def get_all():
    return jsonify([dict(s, reactions=reactions.get(s["id"], {})) for s in ALL_SHAAYARIS])

@app.route("/api/react", methods=["POST"])
def react():
    data = request.json or {}
    sid, rkey = data.get("id"), data.get("emoji")
    if not sid or not rkey:
        return jsonify({"error": "missing"}), 400
    reactions.setdefault(sid, {})[rkey] = reactions.get(sid, {}).get(rkey, 0) + 1
    return jsonify({"ok": True, "reactions": reactions[sid]})

@app.route("/api/comment", methods=["POST"])
def add_comment():
    data = request.json or {}
    sid  = data.get("id")
    name = data.get("name", "Ek Musafir")
    text = data.get("text", "").strip()
    if not sid or not text:
        return jsonify({"error": "missing"}), 400
    comments.setdefault(sid, []).append({
        "name": name, "text": text,
        "time": datetime.now().strftime("%d %b %Y")
    })
    return jsonify({"ok": True, "comments": comments[sid]})

@app.route("/api/comments/<sid>")
def get_comments(sid):
    return jsonify(comments.get(sid, []))

@app.route("/api/stats")
def stats():
    return jsonify({"total": len(ALL_SHAAYARIS)})

if __name__ == "__main__":
    print(f"\n  🌙 Digital Mushayara — {len(ALL_SHAAYARIS)} shaayaris")
    print(f"  Open: http://localhost:5000\n")
    app.run(port=5000, debug=False)
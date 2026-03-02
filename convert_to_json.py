"""
╔══════════════════════════════════════════════════════╗
║   DIGITAL MUSHAYARA — Shaayari Converter             ║
║   Converts your .txt files → shaayaris.json          ║
║   Double-click to run!                               ║
╚══════════════════════════════════════════════════════╝
"""

from pathlib import Path
import json, os

# ── Find latest backup folder ──
BACKUP_ROOT = Path.home() / "Documents" / "Shaayari_Backups"

def get_shaayari_folder():
    if not BACKUP_ROOT.exists():
        return None
    folders = sorted([f for f in BACKUP_ROOT.iterdir() if f.is_dir()], reverse=True)
    for folder in folders:
        p = folder / "Shaayari"
        if p.exists():
            return p
    return None

# ── Parse one file ──
def parse(filepath):
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

    return {
        "id":    Path(filepath).stem,
        "title": title,
        "body":  body,
        "tags":  tags[:2],
    }

# ── Main ──
print("\n" + "="*50)
print("   🌙  Digital Mushayara — Converter")
print("="*50)

folder = get_shaayari_folder()
if not folder:
    print(f"\n  ❌ No shaayari folder found in:")
    print(f"     {BACKUP_ROOT}")
    print(f"\n  Make sure your backup has run at least once!")
    input("\n  Press Enter to exit...")
    exit()

files = [f for f in folder.glob("*.txt") if not f.name.startswith("_")]
print(f"\n  📂 Found folder: {folder}")
print(f"  📝 Found {len(files)} files\n")

shaayaris = []
failed    = []

for f in sorted(files):
    s = parse(f)
    if s:
        shaayaris.append(s)
        print(f"  ✓  {s['title'][:50]}")
    else:
        failed.append(f.name)
        print(f"  ✗  {f.name} (skipped)")

# ── Save JSON next to this script ──
out_path = Path(__file__).parent / "shaayaris.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(shaayaris, f, ensure_ascii=False, indent=2)

print("\n" + "="*50)
print(f"  ✅ Converted {len(shaayaris)} shaayaris!")
if failed:
    print(f"  ⚠  Skipped {len(failed)} files")
print(f"\n  📄 Saved to: {out_path}")
print("="*50)
input("\n  Press Enter to exit...")

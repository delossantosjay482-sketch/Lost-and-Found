"""STEP 9 - AI image matching (Pillow only, works offline).
Image score = perceptual dHash (shape) + colour histogram (colour); text score compares name, description, category.
To upgrade later, replace image_similarity() with CNN embeddings (e.g. MobileNet + cosine similarity)."""
from difflib import SequenceMatcher

from PIL import Image

MIN_SCORE = 0.35


def _dhash(path, size=8):
    px = list(Image.open(path).convert("L").resize((size + 1, size)).getdata())
    return [px[r * (size + 1) + c] > px[r * (size + 1) + c + 1] for r in range(size) for c in range(size)]


def _hist(path):
    h = [0] * 48
    for r, g, b in Image.open(path).convert("RGB").resize((64, 64)).getdata():
        h[r // 16] += 1
        h[16 + g // 16] += 1
        h[32 + b // 16] += 1
    total = sum(h)
    return [x / total for x in h]


def image_similarity(p1, p2):
    """0-1 similarity, or None if an image cannot be read."""
    try:
        a, b = _dhash(p1), _dhash(p2)
        shape = 1 - sum(x != y for x, y in zip(a, b)) / len(a)
        colour = sum(min(x, y) for x, y in zip(_hist(p1), _hist(p2))) / 3
        return 0.4 * shape + 0.6 * colour
    except Exception:
        return None


def _text(a, b):
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    shared = set(a.split()) & set(b.split())
    return max(SequenceMatcher(None, a, b).ratio(), len(shared) / max(len(a.split()), len(b.split())))


def match_score(a, b):
    text = 0.6 * _text(a["name"], b["name"]) + 0.3 * _text(a["description"], b["description"]) \
        + 0.1 * (a["category"] == b["category"])
    if a.get("photo_abs") and b.get("photo_abs"):
        img = image_similarity(a["photo_abs"], b["photo_abs"])
        if img is not None:
            return 0.6 * img + 0.4 * text
    return text


def find_matches(item, candidates, top=5):
    scored = [(match_score(item, c), c) for c in candidates if c["id"] != item["id"] or c["kind"] != item["kind"]]
    return sorted([s for s in scored if s[0] >= MIN_SCORE], key=lambda s: s[0], reverse=True)[:top]
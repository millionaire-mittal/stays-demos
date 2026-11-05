"""Build one private demo site per lead.

Usage:
    python build.py                      # build every lead in leads.json
    python build.py example-homestay     # build one lead (or several) by slug

Output: demos/<slug>/index.html, a single self-contained page.
Images are read from demos/<slug>/img/ (hero.jpg, g1.jpg ... gN.jpg).

The build stops with a clear message if a required field or image is missing.
"""
import colorsys
import json
import re
import sys
from html import escape
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote_plus, urlparse

# Where the demos are deployed. Used for absolute link-preview (og:) URLs.
BASE_URL = "https://stays-demos.vercel.app"

HERE = Path(__file__).parent
DEMOS = HERE / "demos"

REQUIRED = [
    "slug", "name", "type", "town", "region", "country", "phone", "whatsapp",
    "rating", "review_count", "maps_link", "checkin", "checkout", "headline",
    "subline", "highlights", "amenities", "reviews", "nearby", "accent",
    "mood", "photos",
]


class LeadError(Exception):
    pass


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate(lead: dict) -> list[str]:
    errs = []
    slug = lead.get("slug") or "?"
    for k in REQUIRED:
        v = lead.get(k)
        if v is None or v == "" or v == []:
            errs.append(f"missing field '{k}'")
    if errs:
        return errs

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errs.append("'slug' must be lowercase letters, digits and dashes")
    if lead["mood"] not in ("light", "dark"):
        errs.append("'mood' must be \"light\" or \"dark\"")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(lead["accent"])):
        errs.append("'accent' must be a 6-digit hex colour like #2f5d46")
    if not re.fullmatch(r"\d{8,15}", str(lead["whatsapp"])):
        errs.append("'whatsapp' must be digits only with country code, e.g. 919876543210")
    try:
        r = float(lead["rating"])
        if not 0 < r <= 5:
            raise ValueError
    except (TypeError, ValueError):
        errs.append("'rating' must be a number between 0 and 5")
    if not isinstance(lead["review_count"], int) or lead["review_count"] < 1:
        errs.append("'review_count' must be a whole number")
    if not isinstance(lead["photos"], int) or lead["photos"] < 1:
        errs.append("'photos' must be a whole number (count of g1.jpg ... gN.jpg)")

    hl = lead["highlights"]
    if not isinstance(hl, list) or len(hl) != 3 or not all(isinstance(h, str) and h.strip() for h in hl):
        errs.append("'highlights' must be exactly 3 short strings")
    rv = lead["reviews"]
    if not isinstance(rv, list) or len(rv) != 3 or not all(
        isinstance(x, dict) and x.get("text") and x.get("name") for x in rv
    ):
        errs.append("'reviews' must be exactly 3 objects with 'text' and 'name'")
    for key in ("amenities", "nearby"):
        if not isinstance(lead[key], list) or not all(isinstance(x, str) and x.strip() for x in lead[key]):
            errs.append(f"'{key}' must be a list of strings")
    rooms = lead.get("rooms")
    if rooms is not None:
        if not isinstance(rooms, list) or not all(
            isinstance(x, dict) and x.get("name") and x.get("sleeps") for x in rooms
        ):
            errs.append("'rooms' must be a list of {name, sleeps, note}")

    # Images
    if not errs:
        img = DEMOS / slug / "img"
        need = ["hero.jpg"] + [f"g{i}.jpg" for i in range(1, lead["photos"] + 1)]
        missing = [n for n in need if not (img / n).is_file()]
        if missing:
            errs.append(f"missing image(s) in demos/{slug}/img/: {', '.join(missing)}")
    return errs


# --------------------------------------------------------------------------
# Colour: whole palette from one accent + mood
# --------------------------------------------------------------------------

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02x}" for c in rgb)


def hls(h, l, s):
    return rgb_to_hex(colorsys.hls_to_rgb(h % 1, max(0, min(1, l)), max(0, min(1, s))))


def luminance(hexc):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in hex_to_rgb(hexc))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def push_contrast(h, l, s, against, target, direction):
    """Move lightness in `direction` until the colour reaches `target` contrast."""
    c = hls(h, l, s)
    for _ in range(100):
        if contrast(c, against) >= target:
            break
        l += 0.01 * direction
        c = hls(h, l, s)
    return c


def palette(accent: str, mood: str) -> dict:
    h, l, s = colorsys.rgb_to_hls(*hex_to_rgb(accent))
    if mood == "dark":
        bg = hls(h, 0.075, min(s, 0.35))
        surface = hls(h, 0.11, min(s, 0.30))
        text = hls(h + 0.06, 0.92, 0.25)
        muted = hls(h, 0.70, 0.12)
        line = hls(h, 0.22, min(s, 0.2))
        acc = push_contrast(h, max(l, 0.45), max(s, 0.35), bg, 4.8, +1)
    else:
        bg = hls(h, 0.955, min(max(s, 0.25), 0.45))
        surface = hls(h, 0.925, min(max(s, 0.22), 0.40))
        text = hls(h, 0.13, min(s, 0.30))
        muted = hls(h, 0.38, min(s, 0.16))
        line = hls(h, 0.84, min(s, 0.22))
        acc = push_contrast(h, min(l, 0.5), max(s, 0.3), bg, 4.5, -1)
    on_acc = "#ffffff" if contrast("#ffffff", acc) >= contrast("#111111", acc) else hls(h, 0.08, 0.3)
    return {
        "bg": bg, "surface": surface, "text": text, "muted": muted,
        "line": line, "accent": acc, "on-accent": on_acc,
        "scheme": "dark" if mood == "dark" else "light",
    }


# --------------------------------------------------------------------------
# Amenity icons (ids match <symbol id="i-..."> sprite in template.html)
# --------------------------------------------------------------------------

ICON_RULES = [
    ("wifi", r"wi-?fi|internet"),
    ("parking", r"parking|car park"),
    ("pool", r"pool|swim"),
    ("breakfast", r"breakfast|meal|food|dining|kitchen-cooked|home-cooked|cook"),
    ("kitchen", r"kitchen"),
    ("snow", r"\bac\b|air.?con|air conditioning"),
    ("flame", r"fire|bonfire|hearth"),
    ("leaf", r"garden|lawn|plantation|estate|organic|farm|coffee"),
    ("mountain", r"mountain|hill|valley|view|trek|hike"),
    ("wave", r"beach|sea|ocean|lake|river"),
    ("paw", r"pet"),
    ("drop", r"hot water|geyser|shower"),
    ("laptop", r"work|desk"),
    ("sun", r"terrace|deck|veranda|balcony|sun"),
    ("car", r"pickup|pick-up|transfer|taxi|airport"),
    ("bike", r"bike|cycle|bicycle|scooter"),
    ("tv", r"\btv\b|television"),
    ("shirt", r"laundry|washing"),
    ("plug", r"power|backup|inverter|generator"),
    ("family", r"family|kid|child"),
]


def icon_for(label: str) -> str:
    low = label.lower()
    for icon, rx in ICON_RULES:
        if re.search(rx, low):
            return icon
    return "dot"


# --------------------------------------------------------------------------
# Maps
# --------------------------------------------------------------------------

def map_query(lead: dict) -> str:
    """Turn a Google Maps link into a keyless embed URL."""
    if lead.get("map_query"):
        q = lead["map_query"]
    else:
        link = lead["maps_link"]
        u = urlparse(link)
        qs = parse_qs(u.query)
        m_at = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", link)
        m_place = re.search(r"/place/([^/@?]+)", u.path)
        if qs.get("q"):
            q = qs["q"][0]
        elif qs.get("query"):
            q = qs["query"][0]
        elif m_place:
            q = unquote_plus(m_place.group(1))
        elif m_at:
            q = f"{m_at.group(1)},{m_at.group(2)}"
        else:
            q = f"{lead['name']}, {lead['town']}, {lead['region']}, {lead['country']}"
    return f"https://www.google.com/maps?q={quote(q)}&output=embed"


# --------------------------------------------------------------------------
# Tiny template engine:  {{key}}  {{this}}  {{this.key}}  {{@num}}
#                        {{#each key}}...{{/each}}   {{#if key}}...{{/if}}
# Values are HTML-escaped. {{{key}}} inserts raw (for pre-built JSON/CSS).
# --------------------------------------------------------------------------

TOKEN = re.compile(r"\{\{\{\s*([\w.@]+)\s*\}\}\}|\{\{\s*([#/]?)(\w+)?\s*([\w.@]*)\s*\}\}")


def parse(src):
    root = []
    stack = [("root", None, root)]
    pos = 0
    for m in TOKEN.finditer(src):
        stack[-1][2].append(src[pos:m.start()])
        pos = m.end()
        raw, sigil, word, arg = m.groups()
        if raw:
            stack[-1][2].append(("var", raw, True))
        elif sigil == "#":
            node = (word, arg, [])
            stack[-1][2].append(node)
            stack.append(node)
        elif sigil == "/":
            if stack[-1][0] != word:
                raise LeadError(f"template: unexpected {{{{/{word}}}}}")
            stack.pop()
        else:
            # `{{this.name}}` tokenises as word="this", arg=".name"
            stack[-1][2].append(("var", (word or "") + (arg or ""), False))
    stack[-1][2].append(src[pos:])
    if len(stack) != 1:
        raise LeadError(f"template: unclosed {{{{#{stack[-1][0]}}}}}")
    return root


def lookup(ctx, path):
    if path == "this":
        return ctx["this"]
    parts = path.split(".")
    cur = ctx
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def render(nodes, ctx):
    out = []
    for n in nodes:
        if isinstance(n, str):
            out.append(n)
        elif n[0] == "var":
            v = lookup(ctx, n[1])
            if v is None:
                raise LeadError(f"template: no value for {{{{{n[1]}}}}}")
            out.append(str(v) if n[2] else escape(str(v), quote=True))
        elif n[0] == "if":
            if lookup(ctx, n[1]):
                out.append(render(n[2], ctx))
        elif n[0] == "each":
            items = lookup(ctx, n[1]) or []
            for i, item in enumerate(items):
                sub = {**ctx, "this": item, "@index": i, "@num": f"{i + 1:02d}"}
                out.append(render(n[2], sub))
        else:
            raise LeadError(f"template: unknown block {n[0]}")
    return "".join(out)


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def gallery_shapes(n: int) -> list[str]:
    """Tile shapes for the 6-column desktop grid, chosen so every count fills
    the grid with no holes. w4 = 4x2 wide, t = 2x3 tall, s = 2x2, h3 = 3x2,
    full = 6x3 panorama."""
    block = ["w4", "t", "s", "s", "t", "w4"]
    tail = {0: [], 1: ["full"], 2: ["h3", "h3"], 3: ["s", "s", "s"],
            4: ["w4", "s", "s", "w4"], 5: ["w4", "s", "s", "s", "s"]}
    if n % 6 == 1 and n > 1:
        # 7, 13, ...: split the last block's closing wide tile into two squares
        return block * (n // 6 - 1) + block[:-1] + ["s", "s"]
    return block * (n // 6) + tail[n % 6]


def fmt_count(n: int) -> str:
    return f"{n:,}"


def context(lead: dict) -> dict:
    slug = lead["slug"]
    img_dir = DEMOS / slug / "img"
    pal = palette(lead["accent"], lead["mood"])
    css_vars = ";".join(f"--{k}:{v}" for k, v in pal.items() if k != "scheme")

    shapes = gallery_shapes(lead["photos"])
    gallery = []
    for i in range(1, lead["photos"] + 1):
        gallery.append({"src": f"img/g{i}.jpg", "index": i - 1, "n": i,
                        "shape": shapes[i - 1], "alt": f"{lead['name']}, photo {i}"})

    rooms = []
    for i, r in enumerate(lead.get("rooms") or [], 1):
        own = f"room{i}.jpg"
        if (img_dir / own).is_file():
            src = f"img/{own}"
        else:  # fall back to gallery photos, cycling
            src = f"img/g{(i - 1) % lead['photos'] + 1}.jpg"
        sleeps = r["sleeps"]
        rooms.append({
            "name": r["name"],
            "sleeps": f"Sleeps {sleeps}" if isinstance(sleeps, int) else str(sleeps),
            "note": r.get("note", ""),
            "src": src,
            "num": f"{i:02d}",
        })

    reviews = [{"text": r["text"].strip(), "first": r["name"].split()[0]} for r in lead["reviews"]]
    page_url = f"{BASE_URL}/{slug}/"
    rating = float(lead["rating"])

    return {
        **{k: v for k, v in lead.items() if isinstance(v, (str, int, float))},
        "rating": f"{rating:.1f}",
        "review_count": fmt_count(lead["review_count"]),
        "css_vars": css_vars,
        "scheme": pal["scheme"],
        "mood": lead["mood"],
        "highlights": lead["highlights"],
        "gallery": gallery,
        "gallery_count": len(gallery),
        "theme_color": pal["bg"],
        "reviews_count": len(reviews),
        "rooms": rooms,
        "amenities": [{"label": a, "icon": icon_for(a)} for a in lead["amenities"]],
        "reviews": reviews,
        "multi_reviews": len(reviews) > 1,
        "nearby": lead["nearby"],
        "map_src": map_query(lead),
        "page_url": page_url,
        "og_image": page_url + "img/hero.jpg",
        "title": f"{lead['name']} | {lead['type']} in {lead['town']}",
        "description": f"{lead['type']} in {lead['town']}, {lead['region']}. "
                       f"{rating:.1f} stars from {fmt_count(lead['review_count'])} Google reviews. {lead['subline']}",
        "phone_href": "tel:" + re.sub(r"[^\d+]", "", lead["phone"]),
        "wa_href": f"https://wa.me/{lead['whatsapp']}",
        "js_data": json.dumps({"name": lead["name"], "wa": str(lead["whatsapp"])},
                              ensure_ascii=False).replace("</", "<\\/"),
    }


def build(lead: dict, template_nodes) -> Path:
    errs = validate(lead)
    if errs:
        raise LeadError("\n  - " + "\n  - ".join(errs))
    html = render(template_nodes, context(lead))
    out = DEMOS / lead["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    return out


def main(argv):
    try:
        leads = json.loads((HERE / "leads.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"leads.json is not valid JSON: {e}")
    if not isinstance(leads, list):
        sys.exit("leads.json must be a list of lead objects")
    try:
        nodes = parse((HERE / "template.html").read_text(encoding="utf-8"))
    except LeadError as e:
        sys.exit(str(e))

    wanted = argv[1:]
    known = {l.get("slug") for l in leads}
    unknown = [w for w in wanted if w not in known]
    if unknown:
        sys.exit(f"No lead with slug: {', '.join(unknown)} (check leads.json)")
    targets = [l for l in leads if not wanted or l.get("slug") in wanted]
    if not targets:
        sys.exit("leads.json has no leads yet. Add one (see README.md).")

    failed = 0
    for lead in targets:
        try:
            print("built", build(lead, nodes).relative_to(HERE).as_posix())
        except LeadError as e:
            failed += 1
            print(f"FAILED {lead.get('slug', '?')}:{e}", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)

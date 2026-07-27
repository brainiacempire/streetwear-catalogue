#!/usr/bin/env python3
"""Aggregate all scraped rows into one self-contained interactive HTML catalog."""
import json, glob, os, collections, re, hashlib, base64

CATS = [("tee","Tees"),("longsleeve","Longsleeves"),("top","Tops"),
        ("hoodie_sweat","Hoodies & Sweats"),("windrunner","Windrunners & Fleece"),
        ("jeans","Jeans"),("sweats","Sweatpants"),("pants","Pants"),("shorts","Shorts"),
        ("jacket_outerwear","Outerwear"),("footwear","Shoes"),("headwear","Hats"),
        ("accessory","Accessories"),("underwear","Underwear & Socks"),
        ("set","Sets"),("other","Other")]
CATLABEL = dict(CATS)

# Approximate static rates -> GBP. Dave asked for one comparable currency.
# These are indicative, NOT live FX; the original currency is kept on each row
# and shown on the card so nothing is silently misrepresented.
TO_GBP = {
 "GBP":1.0, "USD":0.79, "EUR":0.85, "JPY":0.0052, "CNY":0.11, "KRW":0.00058,
 "AUD":0.52, "CAD":0.58, "NZD":0.47, "HKD":0.101, "SGD":0.59, "TWD":0.024,
 "DKK":0.114, "SEK":0.075, "NOK":0.073, "CHF":0.88, "PLN":0.20, "IDR":0.000048,
 "THB":0.023, "MXN":0.042, "BRL":0.14, "ZAR":0.043, "AED":0.215, "ILS":0.21,
 "INR":0.0094, "TRY":0.023,
}

NEWDROP_DOMAINS = {"sergiotacchini.com","notre-shop.com","silver-raven.co.uk","saintvanity.com",
 "guapi.ch","palyhollywood.com","whensmokeclears.com","abstractclothingclub.com","nyrva.us",
 "digitalgroupi3.com","shopdartisan.com","corteiz.com","crtz.xyz","menacelosangeles.com",
 "badson.us","gabos london","gabos.london","straye.com","peep-game.com","azyrum.com",
 "rh-ude.com","cherrylosangeles.com","warrenlotas.com","whodecideswar.com","kingspider.co",
 "endclothing.com","bstn.com"}

# Brands Dave named or rates: keep their FULL catalog, sold-out included, because
# they function as a reference board. Never let a stock filter hide these.
REFERENCE_DOMAINS = {"satoshinakamoto.cloud","paraphernalia.world","valabasas.com",
                     "thisisneverthat.com","intl.thisisneverthat.com","chromaoffical.com"}
ONLY = None
if os.environ.get("ONLY_DOMAINS"):
    ONLY = set(json.load(open(os.environ["ONLY_DOMAINS"])))
OUT   = os.environ.get("OUT", "streetwear-catalog.html")
TITLE = os.environ.get("TITLE", "Streetwear Catalog")
ALL_STOCK = os.environ.get("ALL_STOCK") == "1"

picks = {}
if os.path.exists("picks.json"):
    for p in json.load(open("picks.json")):
        if p.get("url"):
            picks[p["url"]] = p.get("note", "")
favs = set()
if os.path.exists("favourites.json"):
    try:
        for f in json.load(open("favourites.json")):
            u = f.get("url") if isinstance(f, dict) else f
            if u: favs.add(u)
    except Exception:
        pass
# Brands Dave named or rates: keep their FULL catalog, sold-out included, because
# they function as a reference board. Never let a stock filter hide these.
REFERENCE_DOMAINS = {"satoshinakamoto.cloud","paraphernalia.world","valabasas.com",
                     "thisisneverthat.com","intl.thisisneverthat.com","chromaoffical.com"}
ONLY = None
if os.environ.get("ONLY_DOMAINS"):
    ONLY = set(json.load(open(os.environ["ONLY_DOMAINS"])))
OUT   = os.environ.get("OUT", "streetwear-catalog.html")
TITLE = os.environ.get("TITLE", "Streetwear Catalog")
ALL_STOCK = os.environ.get("ALL_STOCK") == "1"

picks = {}
if os.path.exists("picks.json"):
    for p in json.load(open("picks.json")):
        if p.get("url"):
            picks[p["url"]] = p.get("note", "")
OUTFITS = []
OUTFIT_URLS = set()
if os.path.exists("outfits.json"):
    OUTFITS = json.load(open("outfits.json"))
    for _o in OUTFITS:
        for _v in _o.get("items", {}).values():
            if _v.get("u"): OUTFIT_URLS.add(_v["u"])
vidpicks = {}
if os.path.exists("video_picks.json"):
    for p in json.load(open("video_picks.json")):
        if p.get("url"):
            vidpicks[p["url"]] = p.get("src", "From a video")

# Dave wears trainers/sneakers, loafers, Vans-type — never boots or dressy/"female" shoes.
BOOT_RE = re.compile(r"\bboots?\b|chukka|chelsea|combat|hiking|wellington|\bwellies?\b|desert boot|work ?boot|moc.?toe|\bmoccasin|timberland|red ?wing|blundstone|\bugg\b|tasman|tazz|slipper|danner|palladium|dr\.? ?martens|doc.? ?marten|gore.?tex boot|\bheel|stiletto|\bpumps?\b|ballet|mary.?jane|\bwedge|platform (heel|sandal)|oxford|thigh.?high|knee.?high|court shoe|brogue|derby shoe|monk strap", re.I)

# Title-first classifier — the garment word wins over brand/model names.
# Checked in priority order; footwear only matches real footwear words AND only after
# apparel is ruled out, so "Jordan x Awake Thermal Shirt" reads as a longsleeve, not a shoe.
_CLS_RULES = [
 ("headwear",  r"\b(caps?|hats?|beanies?|snapback|bucket ?hat|59fifty|5[- ]?panel|balaclava|do[- ]?rag|durag|visor|headband)\b"),
 ("underwear", r"\b(socks?|underwear|boxers?|briefs?)\b"),
 ("accessory",  r"\b(belts?|totes?|backpacks?|rucksacks?|wallets?|purses?|card ?holders?|cardholders?|sunglasses|eyewear|goggles|necklaces?|bracelets?|earrings?|pendants?|brooch|keychains?|key ?rings?|scarves|scarf|umbrellas?|gloves?|mittens?|\bbags?\b)\b"),
 ("set",       r"(tracksuit|co[- ]?ords?|two[- ]?piece|2[- ]?piece|matching set|\bset\b)"),
 ("hoodie_sweat", r"\b(hoodie|hooded|sweat ?shirt|crew ?neck|crewneck|zip ?up|zip ?hood|pullover)\b"),
 ("longsleeve", r"\b(long ?sleeve|longsleeve|l/s|thermal|henley)\b"),
 ("tee",       r"\b(t-?shirts?|tees?)\b"),  # explicit tee wins: a graphic tee named after jeans/cargo/denim is still a TEE, not a bottom
 ("jeans",     r"\b(jeans|denim pant|selvedge)\b"),
 ("sweats",    r"\b(sweat ?pants?|sweats|joggers?|track ?pants?|track ?jort)\b"),
 ("shorts",    r"\b(jorts?|shorts?)\b(?!\s*sleeve)"),
 ("pants",     r"\b(pants?|trousers?|chinos?|cargo|slacks|leggings?|pantalon)\b"),
 ("windrunner",r"\b(windrunner|windbreaker|anorak|track ?jacket|track ?top|shell jacket)\b"),
 ("jacket_outerwear", r"\b(jackets?|coats?|parkas?|bomber|puffer|gilet|fleece ?jackets?|fleece ?vest|fleece ?gilet|cardigan|overshirt|shacket|poncho|blouson|veste|manteau|doudoune|blazer(?! ?(low|mid|77)))\b"),
 ("footwear",  r"\b(sneakers?|trainers?|shoes?|footwear|dunk|air ?force|air ?max|air ?jordan|jordan \d|gel[- ]|slides?|sliders?|sandals?|loafers?|mules?|clogs?|crocs?|vans|sk8|old ?skool|runners?|gazelle|samba|campus|superstar|\bforum\b|new balance|\d{3,4}v\d|saucony|\basics\b|onitsuka|\bhoka\b|\bveja\b|superga|novesta|moonstar|\bautry\b|chuck taylor|jack purcell|reebok club|reebok classic)\b"),
 ("tee",       r"\b(t-?shirts?|tees?|s/s|short ?sleeve|jersey|polo)\b"),
 ("top",       r"\b(shirt|top|knit|sweater|button[- ]?up|button[- ]?down|chemise|maille)\b"),
]
_FOOT_EXPLICIT = re.compile(r"\b(sneakers?|trainers?|shoes?|footwear|loafers?|sandals?|slides?|sliders?|mules?|clogs?|crocs?|plimsolls?|espadrilles?)\b", re.I)
_APPAREL_NOUN = re.compile(r"\b(t-?shirts?|tees?|shirts?|hoodie|hooded|sweat|sweats|sweatshirts?|crew ?neck|crewneck|jumper|pullover|pants?|trousers?|chinos?|cargos?|joggers?|shorts?|jorts?|jeans|denim|jacket|coat|parka|bomber|puffer|gilet|vest|cardigan|overshirt|shacket|caps?|hats?|beanies?|socks?|jersey|polo|knit|sweater|longsleeve|long ?sleeve|thermal|henley)\b", re.I)
_CLS = [(k, re.compile(p, re.I)) for k, p in _CLS_RULES]
_NOVELTY = re.compile(r"\b(postcards?|stickers?|magnets?|sponges?|keychains?|earrings?|pins?|badges?|posters?|incense|candles?|mugs?|cups?|saucers?|bowls?|coasters?|plates?|glass|tumblers?|trays?|dish(es)?|ramen|towels?|rugs?|blankets?|ashtrays?|lighters?|air ?fresh|puzzles?|figurines?|keyrings?|ornaments?)\b", re.I)
def classify(title, stored):
    t = title or ""
    if _FOOT_EXPLICIT.search(t):
        return "footwear"                 # literally a shoe/sneaker/loafer/etc.
    apparel = bool(_APPAREL_NOUN.search(t))
    for k, rx in _CLS:
        if apparel and k == "footwear":   # a shoe MODEL name can't steal an apparel piece
            continue
        if rx.search(t):
            if k == "set" and _NOVELTY.search(t):   # a postcard/sticker "set" is not a clothing set
                continue
            return k
    if not apparel:
        for k, rx in _CLS:
            if k == "footwear" and rx.search(t):
                return k
    if stored == "set" and _NOVELTY.search(t):
        return "other"      # scraper-labelled novelty 'set' isn't a clothing set
    return stored

# colour from title when the scraper didn't tag one — feeds the coordination engine
_COL_MAP = [
 ("black", r"\b(black|jet ?black|onyx|noir|blackout)\b"),
 ("white", r"\b(white|off.?white|blanc|optic white)\b"),
 ("grey",  r"\b(grey|gray|charcoal|heather|slate|ash|graphite|cement|steel)\b"),
 ("navy",  r"\b(navy|midnight)\b"),
 ("blue",  r"\b(blue|indigo|cobalt|sky|teal|aqua|denim)\b"),
 ("olive", r"\b(olive|khaki|army|military|sage|moss)\b"),
 ("green", r"\b(green|forest|emerald|lime|hunter|pistachio)\b"),
 ("burgundy", r"\b(burgundy|maroon|wine|oxblood|bordeaux|claret)\b"),
 ("red",   r"\b(red|crimson|scarlet|cherry)\b"),
 ("brown", r"\b(brown|chocolate|coffee|mocha|espresso|walnut|umber|choc)\b"),
 ("tan",   r"\b(tan|camel|beige|sand|taupe|desert|stone|clay)\b"),
 ("cream", r"\b(cream|oat|oatmeal|bone|natural|ecru|vanilla|ivory)\b"),
 ("pink",  r"\b(pink|rose|blush|fuchsia|magenta|salmon)\b"),
 ("purple",r"\b(purple|violet|lilac|lavender|plum)\b"),
 ("orange",r"\b(orange|rust|terracotta|copper|apricot)\b"),
 ("yellow",r"\b(yellow|mustard|gold|amber)\b"),
]
_COL_RX = [(k, re.compile(p, re.I)) for k, p in _COL_MAP]
_NEUT_COLS = {"black","white","grey","navy","brown","tan","cream"}
def colour_of(title, stored):
    # Title-derived colour (word-boundary) is AUTHORITATIVE — the scraper's colour is a
    # substring/tag guess (matched "Stan"->tan, "shredded"->red, or a stray tag colour),
    # which mis-flags pieces and breaks outfit coordination. Fall back to it only if the
    # title yields nothing.
    for k, rx in _COL_RX:
        if rx.search(title or ""): return k
    if stored and stored != "unknown": return stored
    return "unknown"

rows, bad = [], 0
# rows/ = fresh scraped data (refreshed daily by CI); root *.jsonl = permanent
# snapshots that always render: _saved.jsonl (saves), satoshinakamoto/laced (reference).
_rowfiles = sorted(glob.glob("rows/*.jsonl")) + sorted(glob.glob("*.jsonl"))
_seen_rf = set(); _rowfiles = [f for f in _rowfiles if not (f in _seen_rf or _seen_rf.add(f))]
for f in _rowfiles:
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            bad += 1; continue
        t = (o.get("title") or "").strip()
        if not t:
            bad += 1; continue
        tl = t.lower()
        if re.fullmatch(r"(test\s*\d*|\d{1,3})", tl):      continue
        if "gift card" in tl:                              continue
        if re.search(r"\bcrop(?:ped)?\b", tl):             continue   # Dave: no crop tees
        try:    price = float(o.get("price") or 0)
        except Exception: price = 0.0
        if price <= 0 and "mystery" not in tl:             continue
        if price >= 999999:                                continue   # placeholder price
        dom = o.get("domain") or ""
        if ONLY is not None and dom not in ONLY:
            continue
        cat = classify(t, o.get("category") or "other")
        if cat not in CATLABEL: cat = "other"
        sizes = o.get("sizes") or []
        if not isinstance(sizes, list): sizes = []
        url = o.get("url") or ""
        _cur = (o.get("currency") or "USD").upper()
        _g = round(price * TO_GBP.get(_cur, 0.79), 2)
        _saved = url in favs
        _keep = _saved or (url in picks) or (url in vidpicks)
        if not _keep:
            if _g < 5:                 continue   # junk: stickers, samples, £0.13 noise
            if not o.get("image"):     continue   # an imageless card can't be shopped
        if not _saved and _g > 8000:   continue   # £8k+ ceiling: only YOUR saves are ever exempt (kills mislabels/errors)
        if cat=="footwear" and not _saved and BOOT_RE.search(tl): continue   # trainers/sneakers/loafers/vans only
        rows.append({
            "b": (o.get("brand") or o.get("domain") or "?").strip(),
            "d": o.get("domain") or "",
            "t": t, "c": cat, "p": round(price, 2),
            "cur": _cur,
            "g": _g,
            "a": bool(o.get("available")),
            "s": [str(x) for x in sizes][:14],
            "i": o.get("image") or "", "u": url,
            "sm": 1 if o.get("small_only") else 0,          # S-only, won't fit Dave
            "n": picks.get(url, ""),                        # curated note => Best-of shelf
            "v": vidpicks.get(url, ""),                     # video-sourced => Videos shelf
            "f": 1 if url in favs else 0,                   # saved, restored from disk
            "col": colour_of(t, o.get("colour","unknown")),
            # neutrality from the CORRECTED colour only — never the scraper's flag, which
            # mis-marked loud pieces (e.g. kelly-green) as neutral and let them clash in outfits.
            "neu": 1 if colour_of(t, o.get("colour","unknown")) in _NEUT_COLS else 0,
            "nd": 1 if (o.get("new") or (o.get("domain") or "") in NEWDROP_DOMAINS) else 0,
            "np": 1 if o.get("new") else 0,          # genuinely new arrival (published <= 7 days)
        })

# The full dataset is now ~152k rows across 287 stores — far too large to render.
# Build a usable page: everything curated or saved always survives; the rest is
# in-stock, wearable, and capped per brand so no single store floods the grid.
# Domains the user has personally engaged with (saved a piece from) OR that are named
# reference brands are shown in FULL — no cap. Everything else capped per domain.
FULL_DOMAINS = set(REFERENCE_DOMAINS)
try:
    import urllib.parse as _up
    for _f in json.load(open("favourites.json")):
        _u = _f.get("url") if isinstance(_f, dict) else _f
        if _u:
            _h = _up.urlsplit(_u).hostname or ""
            if _h.startswith("www."): _h = _h[4:]
            FULL_DOMAINS.add(_h)
except Exception:
    pass

# Cap per DOMAIN, not per brand: a real label (Cole Buxton, Corteiz) has one domain
# and stays fully shown; only multi-brand mega-shops (Stadium Goods, END, bstn) get
# trimmed. Saved / curated / video / outfit pieces are never dropped.
PER_DOMAIN = int(os.environ.get("PER_DOMAIN", "120"))
FULL_CAP = int(os.environ.get("FULL_CAP", "600"))
MAX_TOTAL = int(os.environ.get("MAX_TOTAL", "42000"))   # hard ceiling: keeps the page fast however many brands we add
import collections as _co
MIN_GBP = float(os.environ.get("MIN_GBP", "0"))   # drop obvious data-error prices from non-saved pieces
perdom = collections.Counter()
rows.sort(key=lambda r: (not (r["n"] or r["v"] or r["f"] or r["np"]), not r["a"], not r["nd"], r["sm"], -(r.get("sc") or 0), -(r["g"] or 0)))
# 1) always keep curated / saved / video / outfit / reference pieces
protected, pool = [], []
for r in rows:
    if MIN_GBP and not r["f"] and (r["g"] or 0) < MIN_GBP:
        continue                      # obvious data-error price on a non-saved piece
    if r["n"] or r["v"] or r["f"] or r["np"] or r["u"] in OUTFIT_URLS or r["d"] in REFERENCE_DOMAINS:
        protected.append(r); continue
    if not ALL_STOCK and (not r["a"] or r["sm"]):
        continue
    pool.append(r)
# 2) fill the rest BALANCED across category AND brand, so no category (sets, tees, shoes...)
#    or brand gets starved by expensive items dominating a global price sort.
budget = max(0, MAX_TOTAL - len(protected))
percat = _co.defaultdict(lambda: _co.defaultdict(list))
for r in pool:
    percat[r["c"]][r["d"]].append(r)   # already best-first from the sort above
CAT_CAP = {"other": 40, "underwear": 30, "accessory": 200}   # keep low-interest buckets modest
cats = [c for c in percat if c != "other"]
if "other" in percat: cats.append("other")
catq = {c: _co.deque(sorted(percat[c].keys())) for c in cats}
catcount, picked = collections.Counter(), []
progress = True
while len(picked) < budget and progress:
    progress = False
    for c in cats:
        if len(picked) >= budget: break
        if catcount[c] >= CAT_CAP.get(c, 10**9): continue
        q = catq[c]
        for _ in range(len(q)):
            d = q[0]; q.rotate(-1)
            lst = percat[c][d]
            dcap = FULL_CAP if d in FULL_DOMAINS else PER_DOMAIN
            if lst and perdom[d] < dcap:
                picked.append(lst.pop(0)); perdom[d] += 1; catcount[c] += 1; progress = True
                break
_picked_urls = set(r["u"] for r in picked)
leftover = [r for r in pool if r["u"] not in _picked_urls]
rows = protected + picked

best = {}
for r in rows:
    k = (r["d"], r["t"].lower())
    cur = best.get(k)
    if cur is None or (r["a"] and not cur["a"]) or (r["a"] == cur["a"] and r["g"] < cur["g"]):
        if cur is not None:                      # keep the better listing but never lose flags
            r["f"] = r["f"] or cur["f"]; r["n"] = r["n"] or cur["n"]; r["v"] = r["v"] or cur["v"]
        best[k] = r
    else:                                        # merge flags onto the survivor
        cur["f"] = cur["f"] or r["f"]; cur["n"] = cur["n"] or r["n"]; cur["v"] = cur["v"] or r["v"]
rows = sorted(best.values(), key=lambda r: (r["b"].lower(), r["t"].lower()))
for i, r in enumerate(rows): r["id"] = i

status = {}
if os.path.exists("status.jsonl"):
    for line in open("status.jsonl", encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: o = json.loads(line)
        except Exception: continue
        status[o.get("domain")] = o

cats    = collections.Counter(r["c"] for r in rows)
brands  = collections.Counter(r["b"] for r in rows)
instock = sum(r["a"] for r in rows)
prices  = [r["g"] for r in rows if r["g"] > 0]
npend   = sum(1 for r in rows if r["n"])
nvid    = sum(1 for r in rows if r["v"])

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "12000"))
_seen_dt = set((r["d"], r["t"].lower()) for r in rows)
_lb = {}
for r in leftover:
    k = (r["d"], r["t"].lower())
    if k in _seen_dt or k in _lb: continue
    _lb[k] = r
leftover = sorted(_lb.values(), key=lambda r: (not r["a"], r["sm"], -(r.get("sc") or 0), -(r["g"] or 0)))
_nid = len(rows)
for r in leftover: r["id"] = _nid; _nid += 1
EXTRA = [leftover[i:i+CHUNK_SIZE] for i in range(0, len(leftover), CHUNK_SIZE)]
DATA   = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
STATUS = json.dumps(sorted(status.values(), key=lambda o: (o.get("status",""), o.get("domain",""))),
                    separators=(",", ":"), ensure_ascii=False)
CATJSON = json.dumps(CATS)
OUTJSON = json.dumps(OUTFITS, separators=(",",":"), ensure_ascii=False)

tpl = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, noimageindex">
<meta name="referrer" content="no-referrer">
<title>__TITLE__</title>
<style>
:root{--bg:#0b0b0d;--panel:#14141a;--panel2:#1b1b23;--line:#2a2a35;--ink:#f2f2f5;
 --dim:#9b9baa;--dim2:#6d6d80;--acc:#d8ff3e;--acc-ink:#14140a;--warn:#ff6b5e;
 --ok:#4ade9b;--fav:#ff4d8d;--new:#5eb4ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Inter,Roboto,sans-serif}
a{color:inherit;text-decoration:none}
header{position:sticky;top:0;z-index:50;background:rgba(11,11,13,.95);
 backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.wrap{max-width:1560px;margin:0 auto;padding:0 20px}
h1{margin:0;font-size:19px;letter-spacing:-.02em;font-weight:650}
.sub{color:var(--dim);font-size:12.5px;margin-top:3px}
.top{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;padding:12px 0 8px}
.stats{margin-left:auto;display:flex;gap:16px;font-size:12.5px;color:var(--dim)}
.stats b{color:var(--ink);font-weight:600}
.chips{display:flex;gap:7px;flex-wrap:wrap;padding-bottom:8px;align-items:center}
.vtsep{width:1px;height:20px;background:var(--line);margin:0 3px}
.collrow{display:inline-flex;gap:7px;flex-wrap:wrap}
#chips{flex-wrap:nowrap;overflow-x:auto;padding:8px 0 9px;border-top:1px solid var(--line);
 scrollbar-width:thin;scrollbar-color:var(--line) transparent}
#chips::-webkit-scrollbar{height:6px}
#chips::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px}
#chips .chip{flex:0 0 auto}
.chip{border:1px solid var(--line);background:var(--panel);color:var(--dim);padding:6px 13px;
 border-radius:999px;font-size:13px;cursor:pointer;transition:.13s;white-space:nowrap;font-weight:500}
.chip:hover{border-color:#3d3d4d;color:var(--ink)}
.chip.on{background:var(--acc);border-color:var(--acc);color:var(--acc-ink);font-weight:650}
.chip .n{opacity:.55;margin-left:5px;font-size:11.5px}
.chip.special{border-color:var(--new);color:var(--new)}
.chip.special.on{background:var(--new);border-color:var(--new);color:#05121e}
.chip.favc{border-color:var(--fav);color:var(--fav)}
.chip.favc.on{background:var(--fav);border-color:var(--fav);color:#1e0510}
.bar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;padding:2px 0 12px}
input[type=search],select{background:var(--panel);border:1px solid var(--line);color:var(--ink);
 padding:8px 12px;border-radius:9px;font-size:13.5px;font-family:inherit}
input[type=search]{min-width:220px}
input[type=search]:focus,select:focus{outline:none;border-color:var(--acc)}
label.tog{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--dim);cursor:pointer;user-select:none}
label.tog input{accent-color:var(--acc);width:15px;height:15px}
.rng{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--dim)}
.rng input{width:115px;accent-color:var(--acc)}
button.act{background:var(--panel);border:1px solid var(--line);color:var(--ink);padding:8px 14px;
 border-radius:9px;cursor:pointer;font-size:13px;font-family:inherit}
button.act:hover{border-color:var(--acc)}
main{padding:20px 0 70px}
.chip.vt{border-color:#3a3a4a;font-weight:650}
.chip.vt.on{background:var(--ink);border-color:var(--ink);color:#0b0b0d}
.fit{background:var(--panel);border:1px solid var(--line);border-radius:14px;
 padding:16px;margin-bottom:18px}
.fit h3{margin:0 0 4px;font-size:15px;font-weight:670;letter-spacing:-.01em}
.fit .blurb{color:var(--dim);font-size:12.5px;margin-bottom:12px;max-width:80ch}
.fit .cost{font-size:14px;font-weight:670;color:var(--acc)}
.slots{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.slot{background:var(--panel2);border:1px solid var(--line);border-radius:10px;overflow:hidden;display:block}
.slot:hover{border-color:#43435a}
.slot .lab{font-size:9.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--acc);
 padding:7px 8px 0;font-weight:700;min-height:26px}
.slot img{width:100%;aspect-ratio:1;object-fit:cover;display:block;margin-top:6px}
.slot .m{padding:8px 9px 10px}
.slot .m .bb{font-size:9.5px;color:var(--dim2);text-transform:uppercase;letter-spacing:.06em;
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.slot .m .tt{font-size:11.5px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;
 -webkit-box-orient:vertical;overflow:hidden;margin:2px 0 4px}
.slot .m .pp{font-size:12.5px;font-weight:660}
.slot .m .cl{font-size:9.5px;color:var(--dim2);margin-left:6px;text-transform:capitalize;font-weight:500}
.fh{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:12px}
.fr{display:flex;align-items:center;gap:10px;white-space:nowrap}
button.act.sm{padding:5px 11px;font-size:12px}
.swap{background:var(--panel);border:1px solid var(--line);color:var(--dim);cursor:pointer;
 font-size:13px;line-height:1;width:24px;height:24px;min-width:24px;flex:0 0 24px;
 border-radius:6px;display:inline-flex;align-items:center;justify-content:center;padding:0}
.swap:hover{color:var(--acc-ink);background:var(--acc);border-color:var(--acc)}
.slot .lab{display:flex;align-items:center;justify-content:space-between}
.fitbar{border-bottom:1px solid var(--line);margin-bottom:16px}
.fitcount{font-size:12.5px;color:var(--dim);margin-left:auto}
.fitsub{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:2px 0 16px}
.tophead{padding:2px 0 18px;border-bottom:1px solid var(--line);margin-bottom:18px}
.toptitle{font-size:19px;font-weight:800;letter-spacing:.2px}
.tophint{color:var(--dim);font-size:13px;margin-top:6px;max-width:760px;line-height:1.5}
.fsub{background:var(--panel);border:1px solid var(--line);color:var(--dim);padding:8px 16px;
 border-radius:9px;cursor:pointer;font-size:13.5px;font-weight:600;font-family:inherit}
.fsub.on{background:var(--ink);border-color:var(--ink);color:#0b0b0d}
.fsub .n{opacity:.5;margin-left:5px;font-size:11.5px}
.fithint{font-size:12px;color:var(--dim2);margin-left:6px}
.builder{display:grid;grid-template-columns:340px 1fr;gap:20px;align-items:start}
@media(max-width:820px){.builder{grid-template-columns:1fr}}
.canvas{position:sticky;top:150px;background:var(--panel);border:1px solid var(--line);
 border-radius:14px;padding:14px}
.cvtop{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.cvtotal{font-size:13px;color:var(--dim)} .cvtotal b{color:var(--acc);font-size:16px}
.cvbtns{display:flex;gap:6px;flex-wrap:wrap}
.cvslots{display:flex;flex-direction:column;gap:8px}
.cvslot{position:relative;border:1px dashed var(--line);border-radius:10px;padding:8px;
 display:flex;gap:10px;align-items:center;cursor:pointer;min-height:56px;transition:.12s}
.cvslot.act{border-style:solid;border-color:var(--acc);background:var(--panel2)}
.cvslot.filled{border-style:solid}
.cvslot .cvlab{font-size:9.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim2);
 font-weight:700;width:52px;flex:0 0 52px}
.cvslot img{width:44px;height:44px;object-fit:cover;border-radius:7px;flex:0 0 44px}
.cvslot .cvm{min-width:0;flex:1}
.cvslot .cvm .bb{font-size:9.5px;color:var(--dim2);text-transform:uppercase;letter-spacing:.05em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cvslot .cvm .tt{font-size:11.5px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cvslot .cvm .pp{font-size:12px;font-weight:660}
.cvbuy{font-size:10.5px;color:var(--acc);font-weight:600;margin-left:6px}
.cvslot .cvadd{color:var(--dim);font-size:12.5px}
.cvslot .rm{position:absolute;top:5px;right:6px;background:none;border:none;color:var(--dim2);
 font-size:15px;cursor:pointer;line-height:1;padding:2px}
.cvslot .rm:hover{color:var(--warn)}
.cvslot .pin{position:absolute;top:5px;right:26px;background:none;border:none;color:var(--dim2);
 font-size:12px;cursor:pointer;line-height:1;padding:2px;filter:grayscale(1);opacity:.5}
.cvslot .pin:hover{opacity:1}
.cvslot .pin.on{filter:none;opacity:1}
.cvslot.lk{border-color:var(--acc)}
button.act.prim{background:var(--acc);border-color:var(--acc);color:var(--acc-ink);font-weight:700}
button.act.prim:hover{filter:brightness(1.05)}
.picker{min-width:0}
.pkhead{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;
 position:sticky;top:150px;background:var(--bg);padding:4px 0;z-index:5}
.pkhead #pktitle{font-size:14px;font-weight:650;margin-right:4px}
.pkgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.pkcard{background:var(--panel);border:1px solid var(--line);border-radius:11px;overflow:hidden;cursor:pointer;transition:.12s}
.pkcard:hover{border-color:var(--acc);transform:translateY(-2px)}
.pkcard img{width:100%;aspect-ratio:1;object-fit:cover;display:block}
.pkcard .pkm{padding:7px 8px 9px}
.pkcard .pkm .bb{font-size:9px;color:var(--dim2);text-transform:uppercase;letter-spacing:.05em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pkcard .pkm .tt{font-size:11px;line-height:1.28;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin:2px 0 3px}
.pkcard .pkm .pp{font-size:11.5px;font-weight:660}
.pkcard .pkm .cl{font-size:9px;color:var(--dim2);margin-left:5px;text-transform:capitalize}
[hidden]{display:none!important}   /* ensure hidden always wins over class display rules */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(212px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:13px;overflow:hidden;
 display:flex;flex-direction:column;transition:.14s;position:relative}
.card:hover{border-color:#43435a;transform:translateY(-2px)}
.card.pend{border-color:#2b4a68}
.ph{aspect-ratio:1;background:var(--panel2);position:relative;overflow:hidden;display:block}
.ph::before{content:"";position:absolute;inset:0;background:
 repeating-linear-gradient(45deg,var(--panel2),var(--panel2) 10px,#191922 10px,#191922 20px);opacity:.5}
.ph img{position:relative;z-index:1}
.ph img{width:100%;height:100%;object-fit:cover;display:block}
.card.out .ph img{filter:grayscale(1) brightness(.5)}
.tagout{position:absolute;top:9px;left:9px;background:rgba(0,0,0,.82);color:var(--warn);
 font-size:10.5px;padding:3px 8px;border-radius:5px;letter-spacing:.04em;font-weight:650}
.tagback{position:absolute;bottom:9px;left:9px;z-index:2;background:#123a1e;color:#7be39a;font-size:9.5px;font-weight:800;letter-spacing:.4px;padding:3px 7px;border-radius:5px;text-transform:uppercase}
.slotout{position:absolute;top:4px;left:4px;z-index:3;background:#3a2020;color:#ff8f8f;font-size:8.5px;font-weight:800;padding:2px 5px;border-radius:4px}
.slotback{position:absolute;top:4px;left:4px;z-index:3;background:#123a1e;color:#7be39a;font-size:8.5px;font-weight:800;padding:2px 5px;border-radius:4px}
.slotw.isout img{opacity:.45}
.fsubtog{margin-left:6px;font-size:12px;color:var(--dim)}
.tagnew{position:absolute;top:9px;left:9px;background:var(--new);color:#05121e;
 font-size:10px;padding:3px 8px;border-radius:5px;letter-spacing:.05em;font-weight:700}
.tagvid{position:absolute;top:9px;left:9px;background:#a978ff;color:#12081f;
 font-size:10px;padding:3px 8px;border-radius:5px;letter-spacing:.05em;font-weight:700}
.note.vnote{color:#a978ff;border-left-color:#a978ff}
.chip.vid{border-color:#a978ff;color:#a978ff}
.chip.vid.on{background:#a978ff;border-color:#a978ff;color:#12081f}
.chip.bw{border-color:#e8e8ee;color:#e8e8ee}
.chip.bw.on{background:#e8e8ee;border-color:#e8e8ee;color:#0b0b0d}
.chip.nd{border-color:#ffb020;color:#ffb020}
.chip.nd.on{background:#ffb020;border-color:#ffb020;color:#0b0b0d}
.tagsm{position:absolute;top:34px;left:9px;background:rgba(0,0,0,.82);color:#ffce6b;
 font-size:10px;padding:3px 7px;border-radius:5px;font-weight:600}
.cat{position:absolute;bottom:9px;right:9px;background:rgba(0,0,0,.72);color:var(--dim);
 font-size:10px;padding:3px 7px;border-radius:5px;text-transform:uppercase;letter-spacing:.05em}
.fav{position:absolute;top:7px;right:7px;z-index:3;width:30px;height:30px;border-radius:50%;
 border:none;background:rgba(0,0,0,.6);color:#fff8;font-size:15px;cursor:pointer;line-height:1;
 display:flex;align-items:center;justify-content:center;transition:.12s;padding:0}
.fav:hover{background:rgba(0,0,0,.85);color:#fff}
.fav.on{background:var(--fav);color:#fff}
.body{padding:11px 12px 13px;display:flex;flex-direction:column;gap:6px;flex:1}
.brand{font-size:10.5px;color:var(--dim2);text-transform:uppercase;letter-spacing:.07em;
 font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.name{font-size:13.5px;line-height:1.32;font-weight:520;display:-webkit-box;
 -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.note{font-size:11px;color:var(--new);line-height:1.35;border-left:2px solid var(--new);padding-left:7px}
.foot{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:8px}
.price{font-size:15px;font-weight:670;letter-spacing:-.01em}
.cc{font-size:10px;color:var(--dim2);font-weight:500;margin-left:5px}
.go{font-size:11.5px;color:var(--acc);font-weight:600}
.sizes{display:flex;gap:3px;flex-wrap:wrap}
.sz{font-size:9.5px;border:1px solid var(--line);color:var(--dim);padding:1.5px 5px;border-radius:4px}
.empty{text-align:center;color:var(--dim);padding:70px 20px}
.more{display:block;margin:26px auto 0;background:var(--panel);border:1px solid var(--line);
 color:var(--ink);padding:11px 26px;border-radius:10px;cursor:pointer;font-size:14px;font-family:inherit}
.more:hover{border-color:var(--acc)}
details.health{margin-top:34px;border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:0 16px}
details.health summary{cursor:pointer;padding:14px 0;font-size:14px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);color:var(--dim)}
th{color:var(--dim2);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
td.st-ok{color:var(--ok)} td.st-bad{color:var(--warn)}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--acc);
 color:var(--acc-ink);padding:11px 20px;border-radius:10px;font-size:13.5px;font-weight:600;
 opacity:0;pointer-events:none;transition:.2s;z-index:99}
#toast.show{opacity:1}
.pkcard{position:relative}
.pfav,.cvfav,.sfav{position:absolute;top:5px;left:5px;z-index:4;background:rgba(11,11,13,.74);border:none;
 color:#9aa2ad;font-size:12px;line-height:1;padding:4px 6px;border-radius:6px;cursor:pointer;filter:grayscale(1);opacity:.9}
.pfav:hover,.cvfav:hover,.sfav:hover{opacity:1;color:#fff}
.pfav.on,.cvfav.on,.sfav.on{filter:none;color:#ff5c8a;opacity:1}
.cvslot .shuf{position:absolute;top:5px;right:46px;background:none;border:none;color:var(--dim2);font-size:14px;cursor:pointer;line-height:1;padding:2px}
.cvslot .shuf:hover{color:#fff}
.slotw{position:relative}
.cvslot .inc{font-size:9px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;padding:2px 7px;border-radius:20px;
 border:1px solid var(--line);background:transparent;color:var(--dim2);cursor:pointer;margin-left:7px;vertical-align:1px}
.cvslot .inc.on{background:var(--acc);border-color:var(--acc);color:var(--acc-ink)}
.cvslot.skip{opacity:.45}
.cvslot.skip .cvadd{text-decoration:line-through}
.savedhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:2px 0 12px;color:var(--dim)}
.savedsearch{background:var(--panel2);border:1px solid var(--line);border-radius:8px;color:#fff;padding:6px 10px;font-size:13px;min-width:200px;flex:1}
.pvwrap{position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:200;display:flex;align-items:center;justify-content:center;padding:24px}
.pvbox{background:var(--panel);border:1px solid var(--line);border-radius:14px;max-width:1120px;width:100%;max-height:90vh;overflow:auto;padding:18px 20px}
.pvhead{display:flex;align-items:center;gap:14px;margin-bottom:14px;position:sticky;top:0}
.pvhead h3{margin:0;font-size:18px}
.pvx{margin-left:auto;background:none;border:none;color:var(--dim);font-size:26px;cursor:pointer;line-height:1}
.pvx:hover{color:#fff}
.pvslots{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}
.pvslots:has(.varrow){display:block}
.pvslots:has(.mqwrap){display:block}
.mqwrap{display:flex;flex-direction:column;align-items:center}
.mqstage{position:relative;width:324px;max-width:84vw;aspect-ratio:9/16;margin:2px auto 0;background:radial-gradient(115% 62% at 50% 6%,#23232e,#0b0b10 72%);border-radius:20px;overflow:hidden}
.mqfloor{position:absolute;left:50%;bottom:2.5%;transform:translateX(-50%);width:48%;height:4%;background:radial-gradient(closest-side,rgba(0,0,0,.6),transparent);border-radius:50%;z-index:1}
.mqsil{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;z-index:2}
.mqsil svg{height:93%;fill:rgba(255,255,255,.05);stroke:rgba(255,255,255,.08);stroke-width:.5}
.mqz{position:absolute;left:50%;transform:translateX(-50%);-webkit-mask-image:radial-gradient(118% 128% at 50% 44%,#000 60%,transparent 90%);mask-image:radial-gradient(118% 128% at 50% 44%,#000 60%,transparent 90%);filter:drop-shadow(0 13px 18px rgba(0,0,0,.55))}
.mqz img{width:100%;height:100%;object-fit:contain;display:block}
.mqz.mqerr{opacity:.1}
.mq-hat{top:2.5%;width:32%;height:11.5%;z-index:7}
.mq-layer{top:11.5%;width:66%;height:36%;z-index:4;opacity:.96}
.mq-top{top:12%;width:55%;height:34%;z-index:5}
.mq-bottom{top:40%;width:51%;height:37%;z-index:5}
.mq-shoe{bottom:3%;width:47%;height:12.5%;z-index:6}
.mq-acc{top:31%;right:1%;left:auto;transform:none;width:22%;height:13%;z-index:6}
.mqcap{font-size:11.5px;color:var(--dim);max-width:322px;text-align:center;margin:13px auto 0;line-height:1.5}
.mq3dhost{position:relative;width:324px;max-width:84vw;height:500px;margin:2px auto 0;background:radial-gradient(120% 60% at 50% 6%,#23232e,#0b0b10 74%);border-radius:20px;overflow:hidden;touch-action:none;cursor:grab}
.mq3dhost canvas{display:block}
.mq3dspin{position:absolute;left:0;right:0;bottom:9px;text-align:center;font-size:10.5px;color:var(--dim);pointer-events:none;letter-spacing:.3px}
.pvslot{background:var(--panel2);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.pvslot img{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:#15151c}
.pvlab{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim2);padding:7px 10px 0}
.pvm{padding:6px 10px 12px}
.pvm .bb{font-size:11px;color:var(--dim2);text-transform:uppercase;letter-spacing:.03em}
.pvm .tt{font-size:13px;margin:2px 0 4px}
.pvm .pp{font-size:14px;font-weight:700}
.pvm .go{display:inline-block;margin-top:6px;font-size:12px;color:var(--acc)}
.varrow{grid-column:1/-1;border-bottom:1px solid var(--line);padding:10px 0}
.varhd{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--dim);margin-bottom:8px}
.varhd b{color:#fff}.varhd .act{margin-left:auto}
.varpcs{display:flex;gap:10px;flex-wrap:wrap}
.varctrl{grid-column:1/-1;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.varctrlh{font-size:12.5px;color:var(--dim);margin-bottom:10px}
.varlocks{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.varlock{background:var(--panel2);border:1px solid var(--line);color:var(--dim);border-radius:8px;padding:7px 10px;font-size:11.5px;cursor:pointer;text-align:left}
.varlock.on{border-color:#ff5c8a;color:#fff}
.varlock .vlx{display:block;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:var(--dim)}
.varlock.on .vlx{color:#ff5c8a}
.varlock .vlk{text-transform:capitalize;font-weight:600;color:#fff}
.vpiece{width:118px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.vpiece.lkd{border-color:#ff5c8a}
.vpiece img{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:#15151c}
.vpt{padding:5px 7px;font-size:10.5px;line-height:1.25;color:var(--dim)}
.vpt .vb{display:block;color:#fff;font-weight:600;text-transform:uppercase;font-size:9.5px}
.vpt .vg{display:block;color:#fff;font-weight:700;margin-top:2px}
.gate{position:fixed;inset:0;z-index:99999;background:#0b0b0f;display:flex;align-items:center;justify-content:center}.gatebox{width:330px;max-width:86vw;text-align:center;color:#eee}.gatelogo{font-size:30px;color:#ff5c8a;margin-bottom:12px}.gatebox h1{font-size:21px;margin:0 0 6px;letter-spacing:.3px}.gatebox p{color:#8a8a93;font-size:13px;margin:0 0 18px;line-height:1.5}.gatebox input{width:100%;padding:12px 14px;border:1px solid #333;background:#15151c;color:#fff;border-radius:10px;font-size:15px;box-sizing:border-box}.gatebox input:focus{outline:none;border-color:#ff5c8a}.gatebox button{width:100%;margin-top:10px;padding:12px;border:0;background:#ff5c8a;color:#111;font-weight:700;border-radius:10px;font-size:15px;cursor:pointer}.gerr{color:#ff6b6b;font-size:12.5px;min-height:16px;margin-top:10px}</style></head><body>
<div id="gate" class="gate" hidden><div class="gatebox"><div class="gatelogo">&#9670;</div><h1>Private</h1><p>Enter your password to view the catalogue.</p><input id="gpw" type="password" placeholder="Password" autocomplete="current-password" autocapitalize="off" autocorrect="off" spellcheck="false"><button id="gbtn">Enter</button><div id="gerr" class="gerr"></div></div></div>
<header><div class="wrap">
 <div class="top">
  <div><h1>__TITLE__</h1>
   <div class="sub">__NSTORE__ stores &middot; mens only &middot; prices shown in GBP &middot; tap the heart to save &mdash; saves persist in this browser
    <span id="storewarn"></span></div></div>
  <div class="stats"><span><b>__NROWS__</b> pieces</span><span><b>__NINSTOCK__</b> in stock</span>
   <span><b>__NBRANDS__</b> brands</span><span id="favcount">0 saved</span></div>
 </div>
 <div class="chips" id="viewtabs">
  <button class="chip vt on" data-v="grid">Catalog</button>
  <button class="chip vt" data-v="fits">Outfits<span class="n" id="fitn"></span></button>
  <button class="chip vt" data-v="surprise">&#127922; Surprise</button>
  <span class="vtsep"></span>
  <span id="collections" class="collrow"></span>
 </div>
 <div class="chips" id="chips"></div>
 <div class="bar">
  <input type="search" id="q" placeholder="Search title or brand&hellip;">
  <select id="brand"><option value="">All brands</option></select>
  <select id="sort"><option value="rel">Sort: brand</option><option value="pa">Price: low to high</option>
   <option value="pd">Price: high to low</option><option value="az">Name A&ndash;Z</option><option value="rand">&#127922; Surprise order</option></select>
  <button class="act sm" id="shuffle" title="Shuffle these results">&#127922; Shuffle</button>
  <select id="colf"><option value="">Any colour</option></select>
  <div class="rng">min&nbsp;£<span id="pvmin">0</span>
   <input type="range" id="pmin" min="0" max="600" value="0" step="5"></div>
  <div class="rng">max&nbsp;£<span id="pv">__PMAX__</span>
   <input type="range" id="pmax" min="0" max="__PMAX__" value="__PMAX__" step="5"></div>
  <label class="tog"><input type="checkbox" id="only" checked> in stock only</label>
  <label class="tog"><input type="checkbox" id="fitsme" checked> fits me (hide S&#8209;only)</label>
  <label class="tog"><input type="checkbox" id="hidesaved"> hide saved</label>
  <button class="act" id="copyfav">Copy saved list</button>
  <button class="act" id="dlfav">Download saved</button>
 </div>
</div></header>
<main class="wrap">
 <div class="grid" id="grid"></div>
 <div id="surprise" hidden>
  <div class="tophead"><div class="toptitle">&#127922; Surprise me</div>
   <div class="tophint">A fresh mix of standout pieces and full outfits every time — pure discovery, pulled at random from the whole catalogue. Hit the button for a new set.</div>
   <button class="act sm prim" id="surpriseagain" style="margin-top:12px">&#127922; Surprise me again</button></div>
  <div class="grid" id="surprisepieces"></div>
  <h3 style="margin:26px 0 12px;font-size:16px;font-weight:700">Surprise outfits</h3>
  <div id="surpriseouts"></div>
 </div>
 <div id="fits" hidden>
  <div class="fitsub" id="fitsub">
   <button class="fsub on" data-fs="build">Build a fit</button>
   <button class="fsub" data-fs="top">&#9733; Top Fits<span class="n" id="topn"></span></button>
   <button class="fsub" data-fs="looks">Starter looks<span class="n" id="lookn"></span></button>
   <button class="fsub" data-fs="saved">Saved outfits<span class="n" id="savedn"></span></button>
   <label class="tog fsubtog"><input type="checkbox" id="hidesavedfits"> hide saved outfits</label>
   <span class="fithint">Pick each piece &middot; mix &amp; match &middot; Surprise Me for a starting point</span>
  </div>
  <div id="buildmode">
   <div class="builder">
    <div class="canvas">
     <div class="cvtop">
      <div class="cvtotal">Total&nbsp; <b id="btotal">&pound;0</b></div>
      <div class="cvbtns">
       <button class="act sm prim" id="bfill">&#10022; Fill the rest</button>
       <button class="act sm" id="brandom">Surprise me</button>
       <button class="act sm" id="bpreview">&#128065; Preview</button>
       <button class="act sm" id="bcopy">Copy fit</button>
       <button class="act sm" id="bclear">Clear</button>
       <button class="act sm prim" id="bsave">&#9829; Save outfit</button>
      </div>
     </div>
     <div class="cvslots" id="cvslots"></div>
    </div>
    <div class="picker">
     <div class="pkhead">
      <span id="pktitle">Choose a piece</span>
      <input type="search" id="pkq" placeholder="Search this slot&hellip;">
      <select id="pkcol"><option value="">Any colour</option></select>
      <label class="tog"><input type="checkbox" id="pkfit" checked> fits me</label>
      <label class="tog"><input type="checkbox" id="pksaved"> saved only</label>
     </div>
     <div class="pkgrid" id="pkgrid"></div>
     <button class="more" id="pkmore" hidden>Show more</button>
    </div>
   </div>
  </div>
  <div id="topmode" hidden>
   <div class="tophead"><div class="toptitle">&#9733; Top Fits</div>
    <div class="tophint" id="tophint"></div></div>
   <div id="toplist"></div>
  </div>
  <div id="looksmode" hidden>
   <div class="bar fitbar">
    <select id="fformula"><option value="">All formulas</option></select>
    <select id="fsort"><option value="">Sort: as generated</option>
     <option value="pa">Total: low to high</option><option value="pd">Total: high to low</option>
     <option value="f">Group by formula</option></select>
    <div class="rng">max total &pound;<span id="fbv">1500</span>
     <input type="range" id="fbudget" min="100" max="1500" value="1500" step="25"></div>
    <span class="fitcount" id="fitcount"></span>
   </div>
   <div id="fitlist"></div>
  </div>
  <div id="savedmode" hidden>
   <div class="savedhead"><span id="savedcount">No saved outfits yet</span>
    <input type="search" id="savedq" placeholder="Search saved outfits&hellip;" class="savedsearch">
    <button class="act sm" id="savedclear" hidden>Clear all</button></div>
   <div id="savedlist"></div>
  </div>
 </div>
 <div class="empty" id="empty" hidden>Nothing matches those filters.</div>
 <button class="more" id="more" hidden>Show more</button>
 <button class="more loadmore" id="loadmore" hidden></button>
 <details class="health"><summary>Source health &mdash; which stores worked, which didn't</summary>
  <table id="htab"><thead><tr><th>Store</th><th>Status</th><th>Products</th><th>Note</th></tr></thead><tbody></tbody></table>
 </details>
</main>
<div id="pvwrap" class="pvwrap" hidden><div class="pvbox">
 <div class="pvhead"><h3 id="pvtitle">Outfit</h3><span id="pvtotal" class="cost"></span>
 <button id="pvbody" class="act sm" title="See the outfit on a figure">&#128100; On the body</button>
 <button id="pvvary" class="act sm" title="A few variations — your liked pieces stay">&#8646; Variations</button>
 <button id="pvclose" class="pvx" title="Close">&times;</button></div>
 <div id="pvslots" class="pvslots"></div></div></div>
<div id="toast"></div>
<script>
const __ENC__=__ENCBLOB__;
const __PLAIN__=__PLAINDATA__;
const __CHUNKS__=__CHUNKSJSON__;
async function _dk(pw,salt,it){var kb=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt:salt,iterations:it,hash:'SHA-256'},kb,{name:'AES-GCM',length:256},false,['decrypt']);}
function _b64(x){var b=atob(x),a=new Uint8Array(b.length),i;for(i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return a;}
async function _unlock(pw){var k=await _dk(pw,_b64(__ENC__.salt),__ENC__.it);var pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:_b64(__ENC__.iv)},k,_b64(__ENC__.ct));return {data:JSON.parse(new TextDecoder().decode(pt)), key:k};}
function startApp(data, _KEY){
const D=data.D, CATS=__CATS__, ST=data.ST, OUT=data.OUT;
let _chunkNext=0;
const PAGE=120; let shown=PAGE, active=new Set(), showPend=false, showFav=false, showVid=false, showBW=false, showND=false;
let _seed=0.37; function _rnd(id){var x=Math.sin((id+1)*97.13+_seed*9973)*10000; return x-Math.floor(x);}
const KEY='streetwear-catalog-saved-v1';
// Saves are keyed by product URL, not row id, so they survive rebuilds where ids shift.
// localStorage works when this file is opened locally; if a sandbox blocks it we fall
// back to memory and the Download button is the safety net.
let STORE_OK=true, _hadSaved=false;
function loadSaved(){
 try{ const raw=localStorage.getItem(KEY); _hadSaved=(raw!=null); return raw? new Set(JSON.parse(raw)) : new Set(); }
 catch(e){ STORE_OK=false; return new Set(); }
}
function persist(){
 try{ localStorage.setItem(KEY, JSON.stringify([...savedUrls])); }
 catch(e){ STORE_OK=false; }
}
const savedUrls = loadSaved();
// Seed from the restored snapshot ONLY on the first ever visit; after that the browser's
// own list is authoritative so removing a saved piece sticks and never silently reappears.
if(!_hadSaved){ D.forEach(r=>{ if(r.f) savedUrls.add(r.u); }); }
const favs=new Set(D.filter(r=>savedUrls.has(r.u)).map(r=>r.id));
const SKEY='streetwear-catalog-stock-v1';
function loadStock(){ try{return JSON.parse(localStorage.getItem(SKEY))||{};}catch(e){return {};} }
const _prevStock=loadStock(); const restocked=new Set();
D.forEach(r=>{ if(savedUrls.has(r.u) && _prevStock[r.u]===false && r.a===true) restocked.add(r.u); });
function saveStockState(){ const st={}; D.forEach(r=>{ if(savedUrls.has(r.u)) st[r.u]=!!r.a; }); try{localStorage.setItem(SKEY,JSON.stringify(st));}catch(e){} }
persist();
const $=id=>document.getElementById(id);
// ---- saved OUTFITS (whole fits) — a separate store from saved pieces ----
const OKEY='streetwear-catalog-outfits-v1';
function loadFits(){ try{const r=localStorage.getItem(OKEY);return r?JSON.parse(r):[];}catch(e){return[];} }
let savedFits=loadFits();
function persistFits(){ try{localStorage.setItem(OKEY,JSON.stringify(savedFits));}catch(e){} }
function updateSavedCount(){ const el=$('savedn'); if(el)el.textContent=savedFits.length; }
function updateFav(){ const n=favs.size; const tot=D.filter(r=>favs.has(r.id)).reduce((a,r)=>a+r.g,0);
 const fc=$('favcount'); if(fc)fc.textContent=n+' saved'+(n?' \u00b7 '+gbp(tot):''); const fn=$('favn'); if(fn)fn.textContent=n; }
function togglePiece(u){ const row=D.find(x=>x.u===u);
 if(savedUrls.has(u)){ savedUrls.delete(u); if(row)favs.delete(row.id); }
 else { savedUrls.add(u); if(row)favs.add(row.id); }
 persist(); updateFav(); return savedUrls.has(u); }
function saveOutfit(items,note){
 const pieces={}; let any=false;
 Object.keys(items).forEach(k=>{ const r=items[k]; if(r){ pieces[k]={u:r.u,b:r.b,t:r.t,g:r.g,i:r.i,c:r.c}; any=true; }});
 if(!any) return 0;
 const sig=Object.values(pieces).map(p=>p.u).sort().join('|');
 if(savedFits.some(f=>Object.values(f.items).map(p=>p.u).sort().join('|')===sig)) return -1;
 savedFits.unshift({items:pieces,note:note||'My fit',total:Object.values(pieces).reduce((a,p)=>a+p.g,0),id:'o'+Date.now()+Math.floor(Math.random()*1000)});
 persistFits(); updateSavedCount(); return 1;
}
const SYM={USD:'$',GBP:'£',EUR:'€',JPY:'¥',CNY:'¥',KRW:'₩',INR:'₹',
 AUD:'A$',CAD:'C$',NZD:'NZ$',HKD:'HK$',SGD:'S$',TWD:'NT$',
 DKK:'kr',SEK:'kr',NOK:'kr',CHF:'CHF ',PLN:'zł',IDR:'Rp',THB:'฿',
 MXN:'MX$',BRL:'R$',ZAR:'R',AED:'AED ',ILS:'₪',TRY:'₺'};
// zero-decimal currencies, and ones where decimals are noise at these magnitudes
const NODEC=new Set(['JPY','KRW','IDR','CLP','VND','HUF','TWD']);
function money(v,c){
 c=(c||'USD').toUpperCase();
 const sym=SYM[c]!==undefined?SYM[c]:(c+' ');
 const n=NODEC.has(c)? Math.round(v).toLocaleString('en-US')
                     : (v%1? v.toFixed(2) : v.toLocaleString('en-US'));
 return sym+n;
}
// everything is compared and filtered in GBP; native price shown underneath
const gbp=v=>'\u00a3'+(v>=100? Math.round(v).toLocaleString('en-US') : v.toFixed(2));
const esc=s=>String(s).replace(/[<>&"]/g,m=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[m]));

const counts={}; D.forEach(r=>counts[r.c]=(counts[r.c]||0)+1);
const nPend=D.filter(r=>r.n).length;
$('collections').innerHTML =
  `<button class="chip special" data-x="pend">&#9733; Best of<span class="n">${nPend}</span></button>`+
  `<button class="chip nd" data-x="nd">&#9889; New In<span class="n">${D.filter(r=>r.np).length}</span></button>`+
  `<button class="chip vid" data-x="vid">Videos<span class="n">${D.filter(r=>r.v).length}</span></button>`+
  `<button class="chip bw" data-x="bw">B/W Tees<span class="n">${D.filter(r=>(r.c==='tee'||r.c==='longsleeve')&&(r.col==='black'||r.col==='white')).length}</span></button>`+
  `<button class="chip favc" data-x="fav">&#9829; Saved<span class="n" id="favn">0</span></button>`;
$('chips').innerHTML =
  CATS.filter(([k])=>counts[k]).map(([k,l])=>
   `<button class="chip" data-c="${k}">${l}<span class="n">${counts[k]}</span></button>`).join('');

function chipClick(e){const b=e.target.closest('.chip'); if(!b||b.classList.contains('vt'))return;
 if(b.dataset.x==='pend'){showPend=!showPend; b.classList.toggle('on');}
 else if(b.dataset.x==='vid'){showVid=!showVid; b.classList.toggle('on');}
 else if(b.dataset.x==='nd'){showND=!showND; b.classList.toggle('on');}
 else if(b.dataset.x==='bw'){showBW=!showBW; b.classList.toggle('on');}
 else if(b.dataset.x==='fav'){showFav=!showFav; b.classList.toggle('on');}
 else if(b.dataset.c){const c=b.dataset.c; active.has(c)?active.delete(c):active.add(c); b.classList.toggle('on');}
 else return;
 shown=PAGE; render();}
$('chips').onclick=chipClick;
$('collections').onclick=chipClick;

{const ff=$('fformula');
 [...new Set(OUT.map(o=>o.formula))].sort().forEach(f=>{
  const op=document.createElement('option'); op.textContent=f; ff.appendChild(op);});}
const bl=[...new Set(D.map(r=>r.b))].sort((a,b)=>a.localeCompare(b));
$('brand').innerHTML+=bl.map(b=>`<option>${esc(b)}</option>`).join('');
{const cols=[...new Set(D.map(r=>r.col).filter(c=>c&&c!=='unknown'))].sort();
 $('colf').innerHTML+=cols.map(c=>`<option value="${c}">${c[0].toUpperCase()+c.slice(1)}</option>`).join('');}

function filtered(){
 const q=$('q').value.trim().toLowerCase(), br=$('brand').value, colf=$('colf').value,
       pm=+$('pmax').value, pn=+$('pmin').value,
       only=$('only').checked, fits=$('fitsme').checked;
 let out=D.filter(r=>
   (!active.size||active.has(r.c)) && (!br||r.b===br) && (!colf||r.col===colf) && (!only||r.a||showFav) &&
   (!fits||!r.sm) && (!showPend||r.n) && (!showVid||r.v) &&
   (!$('hidesaved').checked||showFav||!savedUrls.has(r.u)) &&
   (!showFav||favs.has(r.id)) &&
   (!showND||r.np) &&
   (!showBW||((r.c==='tee'||r.c==='longsleeve')&&(r.col==='black'||r.col==='white'))) &&
   r.g<=pm && r.g>=pn &&
   (!q||r.t.toLowerCase().includes(q)||r.b.toLowerCase().includes(q)));
 const s=$('sort').value;
 if(s==='pa')out=[...out].sort((a,b)=>a.g-b.g);
 else if(s==='pd')out=[...out].sort((a,b)=>b.g-a.g);
 else if(s==='az')out=[...out].sort((a,b)=>a.t.localeCompare(b.t));
 else if(s==='rand')out=[...out].sort((a,b)=>_rnd(a.id)-_rnd(b.id));
 else out=[...out].sort((a,b)=>(b.n?1:0)-(a.n?1:0));
 return out;
}
function card(r){
 const cl=CATS.find(([k])=>k===r.c);
 return `<div class="card${r.a?'':' out'}${r.n?' pend':''}" data-id="${r.id}">
  <button class="fav${favs.has(r.id)?' on':''}" data-fav="${r.id}" title="Save">&#9829;</button>
  <a class="ph" href="${esc(r.u)}" target="_blank" rel="noopener">
   ${r.i?`<img loading="lazy" src="${esc(r.i)}" alt="" onerror="this.remove()">`:''}
   ${r.n?'<span class="tagnew">BEST OF</span>':(r.v?'<span class="tagvid">VIDEO</span>':(r.a?'':'<span class="tagout">SOLD OUT</span>'))}
   ${restocked.has(r.u)?'<span class="tagback">BACK IN STOCK</span>':''}
   ${r.sm?'<span class="tagsm">S only</span>':''}
   <span class="cat">${cl?cl[1]:r.c}</span></a>
  <div class="body"><div class="brand">${esc(r.b)}</div>
   <a class="name" href="${esc(r.u)}" target="_blank" rel="noopener">${esc(r.t)}</a>
   ${r.n?`<div class="note">${esc(r.n)}</div>`:''}
   ${r.v?`<div class="note vnote">${esc(r.v)}</div>`:''}
   ${r.s.length?`<div class="sizes">${r.s.map(z=>`<span class="sz">${esc(z)}</span>`).join('')}</div>`:''}
   <div class="foot"><span class="price">${gbp(r.g)}${r.cur!=='GBP'?`<span class="cc">${money(r.p,r.cur)}</span>`:''}</span>
    <a class="go" href="${esc(r.u)}" target="_blank" rel="noopener">View &rarr;</a></div>
  </div></div>`;
}
function render(){
 const f=filtered();
 $('grid').innerHTML=f.slice(0,shown).map(card).join('');
 updateFav();
 $('empty').hidden=f.length>0;
 $('more').hidden=f.length<=shown;
 $('more').textContent=`Show more (${f.length-shown} left)`;
}
function _favClick(e){
 const b=e.target.closest('[data-fav]'); if(!b)return;
 e.preventDefault();
 const id=+b.dataset.fav;
 const rec=D.find(x=>x.id===id);
 if(favs.has(id)){ favs.delete(id); if(rec) savedUrls.delete(rec.u); }
 else { favs.add(id); if(rec) savedUrls.add(rec.u); }
 persist();
 b.classList.toggle('on');
 updateFav();
 if(showFav) render();
}
$('grid').addEventListener('click',_favClick);
{const sp=$('surprisepieces'); if(sp) sp.addEventListener('click',_favClick);}
function renderSurprise(){
 const pool=D.filter(r=>r.a && r.i);
 const pieces=[...pool].sort(()=>Math.random()-0.5).slice(0,24);
 $('surprisepieces').innerHTML = pieces.length?pieces.map(card).join(''):'<div class="empty">Nothing to surprise you with yet.</div>';
 const outs=[...FITS].sort(()=>Math.random()-0.5).slice(0,6);
 $('surpriseouts').innerHTML = outs.length?outs.map(fitHtml).join(''):'';
}
{const sa=$('surpriseagain'); if(sa) sa.onclick=renderSurprise;}
$('more').onclick=()=>{shown+=PAGE;render()};
$('pmin').addEventListener('input',e=>{$('pvmin').textContent=e.target.value;shown=PAGE;render()});
['q','brand','sort','only','fitsme','colf','hidesaved'].forEach(id=>{const el=$(id); if(el) el.addEventListener('input',()=>{shown=PAGE;render()});});
{const sh=$('shuffle'); if(sh) sh.onclick=()=>{ _seed=Math.random(); $('sort').value='rand'; shown=PAGE; render(); toast('Shuffled \u2014 pick a Sort to go back'); };}
$('pmax').addEventListener('input',e=>{$('pv').textContent=e.target.value;shown=PAGE;render()});
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');
 setTimeout(()=>t.classList.remove('show'),2200);}
$('copyfav').onclick=()=>{
 if(!favs.size){toast('Nothing saved yet');return;}
 const txt=D.filter(r=>favs.has(r.id))
   .map(r=>`${r.b} — ${r.t} — ${gbp(r.g)} — ${r.u}`).join('\n');
 navigator.clipboard.writeText(txt).then(()=>toast(favs.size+' saved items copied'),
   ()=>toast('Copy failed — select manually'));
};
$('dlfav').onclick=()=>{
 if(!favs.size){toast('Nothing saved yet');return;}
 const data=D.filter(r=>favs.has(r.id)).map(r=>({url:r.u,brand:r.b,title:r.t,price:r.p,cur:r.cur}));
 const b=new Blob([JSON.stringify(data,null,1)],{type:'application/json'});
 const a=document.createElement('a');
 a.href=URL.createObjectURL(b); a.download='saved-items.json'; a.click();
 toast(favs.size+' saved items downloaded');
};
if(!STORE_OK){ const w=$('storewarn');
 if(w) w.innerHTML=' &middot; <b style="color:#ff6b5e">this preview can\'t store saves &mdash;'+
   ' open the downloaded file, or use Download saved</b>'; }
const SLOTORDER=['hat','layer','top','bottom','shoe','accessory'];
$('fitn').textContent=OUT.length;
const lookn=$('lookn'); if(lookn) lookn.textContent=OUT.length;

// ===== BUILDER =====
const CVSLOTS=[
 {k:'hat',   label:'Hat',            cats:['headwear']},
 {k:'layer', label:'Jacket / Layer', cats:['jacket_outerwear','windrunner']},
 {k:'top',   label:'Top',            cats:['tee','longsleeve','top','hoodie_sweat']},
 {k:'bottom',label:'Bottom',         cats:['jeans','pants','sweats','shorts']},
 {k:'shoe',  label:'Shoes',          cats:['footwear']},
 {k:'accessory', label:'Extra',      cats:['accessory','underwear']},
];
const CVCOLS=['black','white','grey','cream','tan','brown','navy','blue','green','olive','red','burgundy','pink','purple','orange','yellow'];
let outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
let activeSlot='top', pkShown=60, builderReady=false;

const byCat={}; D.forEach(r=>{ (byCat[r.c]=byCat[r.c]||[]).push(r); });
// ----- Load more pieces: merge extra encrypted chunks into the same catalogue -----
function reindex(quiet){
 const counts={}; D.forEach(r=>counts[r.c]=(counts[r.c]||0)+1);
 $('chips').innerHTML = CATS.filter(([k])=>counts[k]).map(([k,l])=>
   `<button class="chip${active.has(k)?' on':''}" data-c="${k}">${l}<span class="n">${counts[k]}</span></button>`).join('');
 $('collections').innerHTML =
   `<button class="chip special${showPend?' on':''}" data-x="pend">&#9733; Best of<span class="n">${D.filter(r=>r.n).length}</span></button>`+
   `<button class="chip nd${showND?' on':''}" data-x="nd">&#9889; New In<span class="n">${D.filter(r=>r.np).length}</span></button>`+
   `<button class="chip vid${showVid?' on':''}" data-x="vid">Videos<span class="n">${D.filter(r=>r.v).length}</span></button>`+
   `<button class="chip bw${showBW?' on':''}" data-x="bw">B/W Tees<span class="n">${D.filter(r=>(r.c==='tee'||r.c==='longsleeve')&&(r.col==='black'||r.col==='white')).length}</span></button>`+
   `<button class="chip favc${showFav?' on':''}" data-x="fav">&#9829; Saved<span class="n" id="favn">0</span></button>`;
 const cb=$('brand').value;
 const bl=[...new Set(D.map(r=>r.b))].sort((a,b)=>a.localeCompare(b));
 $('brand').innerHTML='<option value="">All brands</option>'+bl.map(b=>`<option>${esc(b)}</option>`).join(''); $('brand').value=cb;
 const cc=$('colf').value;
 const cols=[...new Set(D.map(r=>r.col).filter(c=>c&&c!=='unknown'))].sort();
 $('colf').innerHTML='<option value="">Any colour</option>'+cols.map(c=>`<option value="${c}">${c[0].toUpperCase()+c.slice(1)}</option>`).join(''); $('colf').value=cc;
 for(const k in byCat) delete byCat[k]; D.forEach(r=>{ (byCat[r.c]=byCat[r.c]||[]).push(r); });
 D.forEach(r=>{ if(savedUrls.has(r.u)) favs.add(r.id); });
 if(!quiet) render();
 else { // background fill: keep the "Show more" affordance in sync without resetting the grid
   try{ const f=filtered(); const btn=$('more'); if(btn){ btn.hidden=f.length<=shown; if(f.length>shown) btn.textContent=`Show more (${f.length-shown} left)`; } }catch(e){}
 }
}
function updateLoadMore(){ const btn=$('loadmore'); if(btn) btn.hidden=true; return;
 if(_chunkNext>=__CHUNKS__.length){ btn.hidden=true; }
 else { btn.hidden=false; btn.textContent='\u002b Load more pieces'; } }
let _loadingChunk=false;
async function loadMore(){
 const btn=$('loadmore');
 if(_loadingChunk || _chunkNext>=__CHUNKS__.length){ updateLoadMore(); return; }
 _loadingChunk=true; if(btn){ btn.disabled=true; btn.textContent='Loading\u2026'; }
 try{
   const raw=await fetch(__CHUNKS__[_chunkNext],{cache:'force-cache'}).then(r=>r.json());
   let pieces;
   if(_KEY){ const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:_b64(raw.iv)},_KEY,_b64(raw.ct)); pieces=JSON.parse(new TextDecoder().decode(pt)).D; }
   else { pieces=raw.D; }
   for(const r of pieces) D.push(r);
   _chunkNext++;
   reindex();
   toast('Loaded '+pieces.length+' more pieces');
 }catch(e){ toast('Could not load more pieces'); }
 _loadingChunk=false; if(btn) btn.disabled=false; updateLoadMore();
}
async function loadAllChunks(){ while(_chunkNext<__CHUNKS__.length){ await loadMore(); } }
// Background-fill the FULL library so the randomizer, Surprise, build-a-fit and every
// count work off everything — not just the first batch. Runs after first paint; uses a
// quiet reindex so it never resets the grid you're looking at while browsing.
let _bgFilling=false,_bgDone=false;
async function loadAllQuiet(){
 if(_bgFilling||_bgDone) return; _bgFilling=true;
 let stubborn=0;
 while(_chunkNext<__CHUNKS__.length){
   if(_loadingChunk){ await new Promise(r=>setTimeout(r,200)); continue; }
   _loadingChunk=true;
   let ok=false;
   for(let attempt=0; attempt<3 && !ok; attempt++){
     try{
       const raw=await fetch(__CHUNKS__[_chunkNext],{cache:'force-cache'}).then(r=>{ if(!r.ok) throw new Error('http'); return r.json(); });
       let pieces;
       if(_KEY){ const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:_b64(raw.iv)},_KEY,_b64(raw.ct)); pieces=JSON.parse(new TextDecoder().decode(pt)).D; }
       else { pieces=raw.D; }
       for(const r of pieces) D.push(r);
       _chunkNext++; ok=true;
       reindex(true);
     }catch(e){ await new Promise(r=>setTimeout(r,700)); }   // transient (network/contention) — retry quietly
   }
   _loadingChunk=false;
   if(!ok){ if(++stubborn>=2) break; await new Promise(r=>setTimeout(r,1500)); continue; }  // give up only after repeated failure; retries next visit
   updateLoadMore();
   await new Promise(r=>setTimeout(r,140));
 }
 _bgFilling=false;_bgDone=true;
}
{const lb=$('loadmore'); if(lb) lb.onclick=loadMore;}
const cvTotal=()=>Object.values(outfit).reduce((a,b)=>a+(b?b.g:0),0);

const locked={};
// which slots Fill / Surprise are allowed to touch. Hat/top/bottom/shoe on by default;
// jacket & extra off so nothing you didn't ask for gets added.
const include={hat:true,layer:false,top:true,bottom:true,shoe:true,accessory:false};
function renderCanvas(){
 $('cvslots').innerHTML=CVSLOTS.map(s=>{
  const r=outfit[s.k], act=s.k===activeSlot?' act':'', lk=locked[s.k]?' lk':'';
  const inc=`<button class="inc${include[s.k]?' on':''}" data-inc="${s.k}" title="${include[s.k]?'Will be filled — click to skip this slot':'Skipped — click to include in Fill / Surprise'}">${include[s.k]?'\u2713 fill':'skip'}</button>`;
  const sk=include[s.k]?'':' skip';
  if(r) return `<div class="cvslot filled${act}${lk}${sk}" data-slot="${s.k}">
    <button class="pin${locked[s.k]?' on':''}" data-lock="${s.k}" title="${locked[s.k]?'Locked — kept when filling':'Lock this piece'}">&#128204;</button>
    <button class="cvfav${savedUrls.has(r.u)?' on':''}" data-cvfav="${s.k}" title="Save this piece">&#9829;</button>
    <button class="shuf" data-shuf="${s.k}" title="Swap for another coordinating piece">&#8635;</button>
    <button class="rm" data-rm="${s.k}" title="Remove">&times;</button>
    <div class="cvlab">${s.label}${inc}</div>
    <img src="${esc(r.i)}" alt="" onerror="this.remove()">
    <div class="cvm"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>
     <div class="pp">${gbp(r.g)} <a class="cvbuy" href="${esc(r.u)}" target="_blank" rel="noopener" data-buy>View &rarr;</a></div></div></div>`;
  return `<div class="cvslot empty${act}${sk}" data-slot="${s.k}">
    <div class="cvlab">${s.label}${inc}</div><div class="cvadd">${include[s.k]?'+ choose':'skipped'}</div></div>`;
 }).join('');
 $('btotal').textContent=gbp(cvTotal());
}
function pickerPool(){
 const s=CVSLOTS.find(x=>x.k===activeSlot);
 const q=$('pkq').value.trim().toLowerCase(), col=$('pkcol').value, fit=$('pkfit').checked, sv=$('pksaved').checked;
 let out=[]; s.cats.forEach(c=>(byCat[c]||[]).forEach(r=>out.push(r)));
 out=out.filter(r=>r.a && r.i && (!fit||!r.sm) && (!col||r.col===col) && (!sv||favs.has(r.id)) &&
   (!q||r.t.toLowerCase().includes(q)||r.b.toLowerCase().includes(q)));
 out.sort((a,b)=>(b.f-a.f)||((b.n?1:0)-(a.n?1:0))||(a.g-b.g));
 return out;
}
function renderPicker(){
 const s=CVSLOTS.find(x=>x.k===activeSlot);
 $('pktitle').textContent='Choose: '+s.label;
 const pool=pickerPool();
 $('pkgrid').innerHTML=pool.slice(0,pkShown).map(r=>
  `<div class="pkcard" data-pick="${r.id}" title="${esc(r.b)} — ${esc(r.t)}">
    <button class="pfav${savedUrls.has(r.u)?' on':''}" data-pfav="${r.id}" title="Save this piece">&#9829;</button>
    <img loading="lazy" src="${esc(r.i)}" alt="" onerror="this.remove()">
    <div class="pkm"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>
     <div class="pp">${gbp(r.g)}<span class="cl">${esc(r.col||'')}</span></div></div></div>`
 ).join('') || '<div class="empty">Nothing in stock matches — loosen the filters.</div>';
 $('pkmore').hidden=pool.length<=pkShown;
 $('pkmore').textContent=`Show more (${Math.max(0,pool.length-pkShown)} left)`;
}
function setSlot(k){activeSlot=k; pkShown=60; renderCanvas(); renderPicker();
 document.querySelector('.picker').scrollIntoView({block:'nearest'});}
function initBuilder(){
 if(builderReady) return; builderReady=true;
 $('pkcol').innerHTML+=CVCOLS.map(c=>`<option value="${c}">${c[0].toUpperCase()+c.slice(1)}</option>`).join('');
 renderCanvas(); renderPicker();
}
$('cvslots').addEventListener('click',e=>{
 if(e.target.closest('[data-buy]')){e.stopPropagation(); return;}
 const ic=e.target.closest('[data-inc]');
 if(ic){e.stopPropagation(); const k=ic.dataset.inc; include[k]=!include[k]; renderCanvas(); return;}
 const fv=e.target.closest('[data-cvfav]');
 if(fv){e.stopPropagation(); const k=fv.dataset.cvfav; if(outfit[k]){const on=togglePiece(outfit[k].u); fv.classList.toggle('on',on); toast(on?'Piece saved':'Removed from saved');} return;}
 const sh=e.target.closest('[data-shuf]');
 if(sh){e.stopPropagation(); const k=sh.dataset.shuf; const alt=coordPick(k,heroColour()); if(alt){outfit[k]=alt; renderCanvas();} return;}
 const lk=e.target.closest('[data-lock]');
 if(lk){e.stopPropagation(); const k=lk.dataset.lock; locked[k]=!locked[k]; renderCanvas();
   toast(locked[k]?'Locked — kept when you fill or surprise':'Unlocked'); return;}
 const rm=e.target.closest('[data-rm]');
 if(rm){e.stopPropagation(); const k=rm.dataset.rm; outfit[k]=null; locked[k]=false; renderCanvas(); return;}
 const sl=e.target.closest('[data-slot]'); if(sl) setSlot(sl.dataset.slot);
});
$('pkgrid').addEventListener('click',e=>{
 const fv=e.target.closest('[data-pfav]');
 if(fv){ e.stopPropagation(); const rr=D.find(x=>x.id===+fv.dataset.pfav);
   if(rr){ const on=togglePiece(rr.u); fv.classList.toggle('on',on); toast(on?'Piece saved':'Removed from saved'); } return; }
 const c=e.target.closest('[data-pick]'); if(!c)return;
 const r=D.find(x=>x.id===+c.dataset.pick); if(!r)return;
 outfit[activeSlot]=r; renderCanvas();
 const order=CVSLOTS.map(s=>s.k), ci=order.indexOf(activeSlot);
 const rot=order.slice(ci+1).concat(order.slice(0,ci+1));
 const nextEmpty=rot.find(k=>!outfit[k]);
 if(nextEmpty) setSlot(nextEmpty); else renderPicker();
});
['pkq','pkcol','pkfit','pksaved'].forEach(id=>$(id).addEventListener('input',()=>{pkShown=60;renderPicker();}));
$('pkmore').onclick=()=>{pkShown+=60;renderPicker();};

// ---- curated, cross-brand, STYLE- and colour-coordinated selection ----
function usedBrands(exceptK){ const s=new Set(); SLOTORDER.forEach(k=>{ if(k!==exceptK && outfit[k]) s.add((outfit[k].b||'').toLowerCase()); }); return s; }
// style families — a fit reads right when its pieces share a lane
const STYLE_RE={
 tech:/gore|shell|windrun|technical|nylon|cargo|salomon|arc.?teryx|acronym|trail|packable|softshell|gorp|\bhpc\b|3\.?l\b/i,
 work:/carhartt|dickies|chore|workwear|waxed|canvas|\bduck\b|flannel|painter|utility|hickory|\bwork\b/i,
 clean:/selvedge|raw denim|\bchino|trouser|loafer|oxford shirt|knit|cashmere|merino|pleated|tailored|\bwool\b|mohair|\bsilk\b|suit\b/i,
 skate:/skate|\bvans\b|polar|thrasher|palace|baker|emerica|krooked|spitfire|\bhuf\b|\bdc\b/i,
 sport:/\btrack\b|jersey|\bsport|running|athletic|\bgym\b|warm.?up|\bnike\b|adidas|reebok|new balance|\basics\b|jordan|\bpuma\b/i
};
function styleOf(r){ const t=((r.b||'')+' '+(r.t||'')).toLowerCase();
 for(const k in STYLE_RE){ if(STYLE_RE[k].test(t)) return k; } return 'street'; }
function outfitStyle(){ const c={}; SLOTORDER.forEach(k=>{ if(outfit[k]){ const st=styleOf(outfit[k]); c[st]=(c[st]||0)+1; }});
 let best='',n=0; for(const st in c){ if(c[st]>n){ n=c[st]; best=st; } } return best; }
const NEUTC=new Set(['black','white','grey','cream','tan','brown','navy','beige','charcoal','ecru']);
function fitAccents(){ const a=new Set(); SLOTORDER.forEach(k=>{const r=outfit[k]; if(r&&r.col&&r.col!=='unknown'&&!NEUTC.has(r.col)&&!r.neu)a.add(r.col);}); return a; }
// colour harmony vs the pieces already placed: neutral base + at most one accent, or tonal
function harmC(r,acc){ if(!r.col||r.col==='unknown')return 0; if(NEUTC.has(r.col)||r.neu)return 3;
 if(acc.has(r.col))return 5; if(acc.size===0)return 2; return -6; }
function rndFrom(cats,filt,k,style){
 let pool=[]; cats.forEach(c=>(byCat[c]||[]).forEach(r=>{if(r.a&&r.i&&!r.sm)pool.push(r);}));
 if(filt)pool=pool.filter(filt);
 if(!pool.length)return null;
 const ub=usedBrands(k);
 const fresh=pool.filter(r=>!ub.has((r.b||'').toLowerCase()));
 if(fresh.length) pool=fresh;
 const acc=fitAccents();
 // reason: COLOUR HARMONY with what's placed, then STYLE (goes-together), then quality, then price
 pool.sort((a,b)=>
   (harmC(b,acc)-harmC(a,acc))
   ||(style?((styleOf(b)===style?1:0)-(styleOf(a)===style?1:0)):0)
   ||(b.f-a.f)||((b.n?1:0)-(a.n?1:0))||((b.v?1:0)-(a.v?1:0))
   ||((a.col==='unknown'?1:0)-(b.col==='unknown'?1:0))||(a.g-b.g));
 const head=pool.slice(0,Math.max(12,Math.floor(pool.length*0.18)));
 return head[Math.floor(Math.random()*head.length)];
}
const catsOf=k=>CVSLOTS.find(s=>s.k===k).cats;
// the hero colour = colour of the placed top, else the loudest placed non-neutral piece
function heroColour(){
 if(outfit.top && outfit.top.col && outfit.top.col!=='unknown') return outfit.top.neu?null:outfit.top.col;
 for(const k of ['layer','hat','shoe','bottom']){const r=outfit[k];
   if(r && !r.neu && r.col && r.col!=='unknown') return r.col;}
 return null;
}
// pick a coordinating piece for one slot given the hero colour
function coordPick(k,hero){
 const c=catsOf(k), st=outfitStyle();
 if(k==='top')   return rndFrom(c,r=>!r.neu&&r.col!=='unknown',k,st)||rndFrom(c,r=>!r.neu,k,st)||rndFrom(c,null,k,st);
 if(k==='bottom')return rndFrom(c,r=>r.neu&&r.col!=='unknown',k,st)||rndFrom(c,r=>r.neu,k,st)||rndFrom(c,null,k,st);
 if(k==='hat')   return (hero&&rndFrom(c,r=>r.col===hero,k,st))||rndFrom(c,r=>r.neu&&r.col!=='unknown',k,st)||rndFrom(c,r=>r.neu,k,st)||rndFrom(c,null,k,st);
 // footwear: mainly trainers/sneakers, clean & style-matched — loafers are a rare exception, never random
 if(k==='shoe'){ const snk=r=>/sneaker|trainer|\bdunk\b|air ?force|air ?max|jordan|gel[- ]|\brunner|gazelle|samba|campus|superstar|new balance|\bnb\b|\bvans\b|sk8|old ?skool|authentic|\b\d{3,4}\b|salomon|asics/i.test(r.t);
   const bad=r=>/loafer|sandal|\bslide|slider|\bmule|\bclog|\bcroc/i.test(r.t);
   return rndFrom(c,r=>snk(r)&&!bad(r)&&r.neu&&r.col!=='unknown',k,st)||rndFrom(c,r=>snk(r)&&!bad(r),k,st)
        ||(hero&&rndFrom(c,r=>!bad(r)&&r.col===hero,k,st))||rndFrom(c,r=>!bad(r)&&r.neu,k,st)||rndFrom(c,r=>!bad(r),k,st)||rndFrom(c,null,k,st); }
 if(k==='layer') return rndFrom(c,r=>r.neu&&r.col!=='unknown',k,st)||rndFrom(c,r=>r.neu,k,st)||rndFrom(c,null,k,st);
 return rndFrom(c,r=>r.col!=='unknown',k,st)||rndFrom(c,null,k,st);
}
// FILL THE REST: fill only the slots you've INCLUDED and haven't locked, coordinated around your picks
$('bfill').onclick=()=>{
 if(include.top && !outfit.top && !locked.top){ outfit.top=coordPick('top',null); }
 let hero=heroColour(), n=0;
 ['top','bottom','shoe','layer','hat','accessory'].forEach(k=>{
   if(include[k] && !outfit[k] && !locked[k]){ outfit[k]=coordPick(k,hero); if(outfit[k]){ n++; hero=hero||heroColour(); } }});
 renderCanvas(); setSlot(activeSlot);
 toast(n? `Filled ${n} slot${n>1?'s':''} — coordinated, cross-brand` : 'Nothing to fill — include some slots, or unlock them');
};
// SURPRISE ME: rebuild every UNLOCKED slot into a fresh coordinated fit
$('brandom').onclick=()=>{
 SLOTORDER.forEach(k=>{ if(include[k] && !locked[k]) outfit[k]=null; });
 if(include.top && !outfit.top){ outfit.top=coordPick('top',null); }
 let hero=heroColour();
 ['bottom','shoe','layer','hat','accessory'].forEach(k=>{
   if(include[k] && !locked[k] && !outfit[k]){ outfit[k]=coordPick(k,hero); hero=hero||heroColour(); }});
 renderCanvas(); setSlot(activeSlot);
 toast('Fresh coordinated fit — lock keepers, skip slots you don\u2019t want, Surprise again');
};
$('bclear').onclick=()=>{outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
 Object.keys(locked).forEach(k=>locked[k]=false); renderCanvas(); setSlot('top');};
$('bsave').onclick=()=>{
 const r=saveOutfit(outfit,'My fit');
 toast(r===1?'Outfit saved to Saved Outfits':r===-1?'That outfit is already saved':'Nothing placed yet');
};
$('bcopy').onclick=()=>{
 const parts=SLOTORDER.filter(k=>outfit[k]).map(k=>`${outfit[k].b} — ${outfit[k].t} — ${gbp(outfit[k].g)} — ${outfit[k].u}`);
 if(!parts.length){toast('Nothing placed yet');return;}
 navigator.clipboard.writeText(parts.join('\n')).then(()=>toast('Outfit copied'),()=>toast('Copy failed'));
};
$('bpreview').onclick=()=>{ if(SLOTORDER.some(k=>outfit[k])) openPreview(outfit,'Your fit',cvTotal()); else toast('Nothing placed yet'); };
// ===== STARTER LOOKS (load into builder) =====
const FITS=OUT.map((o,i)=>({i,formula:o.formula,note:o.note,items:Object.assign({},o.items)}));
const fitTotal=f=>Object.values(f.items).reduce((a,b)=>a+b.g,0);
function slotHtml(r,k){
 return `<div class="slotw">
   <button class="sfav${savedUrls.has(r.u)?' on':''}" data-sfav="${esc(r.u)}" title="Save this piece">&#9829;</button>
   <a class="slot" href="${esc(r.u)}" target="_blank" rel="noopener">
    <div class="lab">${k}</div><img loading="lazy" src="${esc(r.i)}" alt="" onerror="this.remove()">
    <div class="m"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>
     <div class="pp">${gbp(r.g)}</div></div></a></div>`;
}
function fitHtml(f){
 const slots=SLOTORDER.filter(k=>f.items[k]).map(k=>slotHtml(f.items[k],k)).join('');
 return `<div class="fit" id="fit${f.i}">
   <div class="fh"><div><h3>${esc(f.formula)}</h3><div class="blurb">${esc(f.note)}</div></div>
    <div class="fr"><span class="cost">${gbp(fitTotal(f))}</span>
     <button class="act sm" data-preview="${f.i}" title="See it bigger">&#128065; View</button>
     <button class="act sm" data-savelook="${f.i}" title="Save whole outfit">&#9829; Save</button>
     <button class="act sm" data-use="${f.i}">Use &amp; edit</button></div></div>
   <div class="slots">${slots}</div></div>`;
}
function fitSig(f){ return SLOTORDER.map(k=>f.items[k]?f.items[k].u:"").join("|"); }
function savedFitSigs(){ return new Set(savedFits.map(f=>SLOTORDER.map(k=>f.items[k]?f.items[k].u:"").join("|"))); }
function hideSavedFitsOn(){ const el=$("hidesavedfits"); return !!(el&&el.checked); }
function fitsFiltered(){
 const fm=$('fformula').value, bud=+$('fbudget').value, srt=$('fsort').value;
 let out=FITS.filter(f=>(!fm||f.formula===fm)&&fitTotal(f)<=bud);
 if(hideSavedFitsOn()){ const sv=savedFitSigs(); out=out.filter(f=>!sv.has(fitSig(f))); }
 if(srt==='pa')out=[...out].sort((a,b)=>fitTotal(a)-fitTotal(b));
 else if(srt==='pd')out=[...out].sort((a,b)=>fitTotal(b)-fitTotal(a));
 else if(srt==='f')out=[...out].sort((a,b)=>a.formula.localeCompare(b.formula));
 return out;
}
function renderFits(){
 const f=fitsFiltered();
 $('fitlist').innerHTML=f.length?f.map(fitHtml).join(''):'<div class="empty">No looks under that budget.</div>';
 $('fitcount').textContent=`${f.length} of ${FITS.length} looks`;
}
// ===== Top Fits: curated ranking weighted toward the user's actual taste =====
function fitScore(f, prefFormulas, prefBrands){
 let s=0, liked=0, slots=0;
 SLOTORDER.forEach(k=>{ const p=f.items[k]; if(!p) return; slots++;
   if(savedUrls.has(p.u)){ s+=120; liked++; }        // a liked piece dominates — his taste leads
   if(prefBrands.has(p.b)) s+=9;                      // brands he saves from
   if(p.n) s+=10;                                     // curated best-of
   if(p.v) s+=6;                                      // seen in a video
   s+=Math.min(12, p.sc||0);                          // per-piece curation/quality signal
 });
 s+=slots*3;                                          // fuller, more-styled fits
 if(prefFormulas.has(f.formula)) s+=16;               // formulas he saves as outfits
 return {f, s, liked, slots};
}
function renderTop(){
 const prefFormulas=new Set(savedFits.map(x=>x.note));
 const prefBrands=new Set(); D.forEach(r=>{ if(savedUrls.has(r.u)) prefBrands.add(r.b); });
 let pool=FITS;
 if(hideSavedFitsOn()){ const sv=savedFitSigs(); pool=FITS.filter(f=>!sv.has(fitSig(f))); }
 const scored=pool.map(f=>fitScore(f,prefFormulas,prefBrands))
   .sort((a,b)=> b.s-a.s || fitTotal(a.f)-fitTotal(b.f));
 const top=scored.slice(0,60);
 const anyLiked=savedUrls.size>0 || savedFits.length>0;
 const withLiked=top.filter(x=>x.liked>0).length;
 $('topn').textContent=top.length;
 $('tophint').textContent = anyLiked
   ? `Curated from what you\u2019ve liked \u2014 ${withLiked} of the ${top.length} below are built around your saved pieces, with your brands and outfit styles pushed to the top. Heart more and this reshapes around you.`
   : `The flyest coordinated fits across every brand \u2014 distinct labels head to toe, ranked on curation and quality. Heart any piece or outfit and this instantly reshuffles around your taste.`;
 $('toplist').innerHTML = top.length ? top.map(x=>fitHtml(x.f)).join('') : '<div class="empty">No fits to rank yet.</div>';
}
document.addEventListener('click',e=>{
 const u=e.target.closest('[data-use]'); if(!u)return;
 const f=FITS[+u.dataset.use];
 outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
 SLOTORDER.forEach(k=>{ if(f.items[k]) outfit[k]=f.items[k]; });
 setFitSub('build'); initBuilder(); renderCanvas(); setSlot('top');
 toast('Loaded — now swap any piece');
});
{const ff=$('fformula');
 [...new Set(OUT.map(o=>o.formula))].sort().forEach(f=>{const op=document.createElement('option');op.textContent=f;ff.appendChild(op);});}
['fformula','fbudget','fsort'].forEach(id=>{const el=$(id); if(el) el.addEventListener('input',()=>{
  if(id==='fbudget')$('fbv').textContent=$('fbudget').value; renderFits();});});

// ===== sub-tab + view switching =====
document.addEventListener('click',e=>{
 const sf=e.target.closest('[data-sfav]');
 if(sf){ e.preventDefault(); e.stopPropagation(); const on=togglePiece(sf.dataset.sfav); sf.classList.toggle('on',on); toast(on?'Piece saved':'Removed from saved'); return; }
 const sl=e.target.closest('[data-savelook]');
 if(sl){ e.preventDefault(); const f=FITS[+sl.dataset.savelook]; const r=saveOutfit(f.items,f.formula); toast(r===1?'Outfit saved to Saved Outfits':r===-1?'Already saved':'Could not save'); return; }
 const ld=e.target.closest('[data-loadsaved]');
 if(ld){ const f=savedFits[+ld.dataset.loadsaved]; if(!f)return;
   outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
   SLOTORDER.forEach(k=>{ if(f.items[k]){ const p=f.items[k]; outfit[k]=D.find(x=>x.u===p.u)||p; }});
   setFitSub('build'); initBuilder(); renderCanvas(); setSlot('top'); toast('Loaded into the builder'); return; }
 const dl=e.target.closest('[data-delsaved]');
 if(dl){ savedFits.splice(+dl.dataset.delsaved,1); persistFits(); renderSaved(); return; }
});
function renderSaved(){
 updateSavedCount();
 const box=$('savedlist'), cnt=$('savedcount'), clr=$('savedclear');
 const q=($('savedq')?$('savedq').value.trim().toLowerCase():'');
 if(!savedFits.length){ box.innerHTML='<div class="empty">No saved outfits yet — build a fit and hit \u201cSave outfit\u201d, or save a starter look.</div>';
   cnt.textContent='No saved outfits yet'; if(clr)clr.hidden=true; return; }
 cnt.textContent=savedFits.length+' saved outfit'+(savedFits.length>1?'s':''); if(clr)clr.hidden=false;
 box.innerHTML=savedFits.map((f,idx)=>{
  if(q){ const hay=((f.note||'')+' '+Object.values(f.items).map(p=>p.b+' '+p.t).join(' ')).toLowerCase(); if(!hay.includes(q)) return ''; }
  const slots=SLOTORDER.filter(k=>f.items[k]).map(k=>{const r=f.items[k];
    const _cur=D.find(x=>x.u===r.u); const _out=_cur&&!_cur.a; const _back=restocked.has(r.u);
    const _badge=_back?'<span class="slotback">BACK</span>':(_out?'<span class="slotout">SOLD OUT</span>':'');
    return `<div class="slotw${_out?' isout':''}">${_badge}<button class="sfav${savedUrls.has(r.u)?' on':''}" data-sfav="${esc(r.u)}" title="Save this piece">&#9829;</button>`+
     `<a class="slot" href="${esc(r.u)}" target="_blank" rel="noopener"><div class="lab">${k}</div>`+
     `<img loading="lazy" src="${esc(r.i)}" alt="" onerror="this.remove()">`+
     `<div class="m"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div><div class="pp">${gbp(r.g)}</div></div></a></div>`;
  }).join('');
  return `<div class="fit"><div class="fh"><div><h3>${esc(f.note||'Saved outfit')}</h3></div>`+
    `<div class="fr"><span class="cost">${gbp(f.total)}</span>`+
    `<button class="act sm" data-preview-saved="${idx}" title="See it bigger">&#128065; View</button>`+
    `<button class="act sm" data-loadsaved="${idx}">Load</button>`+
    `<button class="act sm" data-delsaved="${idx}">Remove</button></div></div>`+
    `<div class="slots">${slots}</div></div>`;
 }).join('') || '<div class="empty">No saved outfits match that search.</div>';
}
{const sq=$('savedq'); if(sq) sq.addEventListener('input',renderSaved);}
// preview (see a fit bigger) — starter looks + saved outfits
function pvPieces(items){ return SLOTORDER.filter(k=>items[k]).map(k=>{const r=items[k];
   return `<div class="pvslot"><div class="pvlab">${k}</div>`+
     `<img loading="lazy" src="${esc(r.i)}" alt="" onerror="this.style.opacity=.15">`+
     `<div class="pvm"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>`+
     `<div class="pp">${gbp(r.g)}${r.col&&r.col!=='unknown'?' \u00b7 '+esc(r.col):''}</div>`+
     `<a class="go" href="${esc(r.u)}" target="_blank" rel="noopener">View item &rarr;</a></div></div>`;}).join('');
}
function pvMannequin(items){
 const z=(k,cls)=>{const r=items[k]; if(!r)return '';
   return `<div class="mqz ${cls}" title="${esc(r.b)} \u2014 ${esc(r.t)}"><img loading="lazy" src="${esc(r.i)}" onerror="this.parentNode.classList.add('mqerr')"></div>`;};
 const sil='<div class="mqsil"><svg viewBox="0 0 120 240" preserveAspectRatio="xMidYMid meet">'
  +'<circle cx="60" cy="22" r="14"/>'
  +'<path d="M40 40 Q60 33 80 40 L87 68 L74 74 L74 132 L46 132 L46 74 L33 68 Z"/>'
  +'<path d="M41 43 L31 46 L23 100 L31 102 L39 62 Z"/>'
  +'<path d="M79 43 L89 46 L97 100 L89 102 L81 62 Z"/>'
  +'<path d="M47 132 L59 132 L57 228 L48 228 Z"/>'
  +'<path d="M61 132 L73 132 L72 228 L63 228 Z"/></svg></div>';
 const tot=SLOTORDER.filter(k=>items[k]).reduce((a,k)=>a+items[k].g,0);
 const pieces=SLOTORDER.filter(k=>items[k]).length;
 return `<div class="mqwrap"><div class="mqstage"><div class="mqfloor"></div>${sil}`
   +z('hat','mq-hat')+z('layer','mq-layer')+z('top','mq-top')+z('bottom','mq-bottom')+z('shoe','mq-shoe')+z('accessory','mq-acc')
   +`</div><div class="mqcap">${pieces} pieces styled head-to-toe on the figure \u2014 ${gbp(tot)}. Each sits where it's worn, so you get a real feel for the fit. Hover a piece for the brand.</div></div>`;
}
let _pvView='pieces';
function _loadScript(src){return new Promise((res,rej)=>{var el=document.createElement('script');el.src=src;el.onload=res;el.onerror=rej;document.head.appendChild(el);});}
var _threeTried=false,_threeOk=false;
async function ensureThree(){ if(window.THREE)return true; if(_threeTried)return _threeOk; _threeTried=true;
 try{ await Promise.race([_loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'), new Promise(function(_,rej){setTimeout(function(){rej('t');},6000);})]); _threeOk=!!window.THREE; }catch(e){ _threeOk=false; } return _threeOk; }
var _COLHEX={black:0x201f1f,white:0xededea,grey:0x8c8c92,cream:0xe6ddc9,tan:0xc7a97b,brown:0x6a482e,navy:0x243250,blue:0x39599c,green:0x40684a,olive:0x6a6a3c,red:0xb23c3c,burgundy:0x6d2b35,purple:0x6d4a88,orange:0xc77a3c,yellow:0xd6b24c,pink:0xd68a9e,unknown:0x7c7c82};
function _hexFor(r){ return (r&&_COLHEX[r.col])||0x7c7c82; }
function _matFor(r){ var m=new THREE.MeshStandardMaterial({color:_hexFor(r),roughness:.92,metalness:.03});
 if(r&&r.i){ try{ var L=new THREE.TextureLoader(); if(L.setCrossOrigin)L.setCrossOrigin('anonymous');
   L.load(r.i,function(t){ if(THREE.sRGBEncoding)t.encoding=THREE.sRGBEncoding; m.map=t; m.color.set(0xffffff); m.needsUpdate=true; },undefined,function(){}); }catch(e){} }
 return m; }
var _mq3d=null;
function cleanup3D(){ if(_mq3d){ try{cancelAnimationFrame(_mq3d.raf);}catch(e){} try{_mq3d.rnd.dispose();}catch(e){} _mq3d=null; } }
async function init3D(items,host,capEl){
 var ok=await ensureThree();
 if(!ok){ var h2=document.getElementById('pvslots'); if(h2) h2.innerHTML=pvMannequin(items); return; }
 cleanup3D();
 var W=host.clientWidth||320, H=host.clientHeight||500;
 var scene=new THREE.Scene();
 var cam=new THREE.PerspectiveCamera(36,W/H,0.1,100); cam.position.set(0,0.4,8.2);
 var rnd=new THREE.WebGLRenderer({antialias:true,alpha:true}); rnd.setSize(W,H); rnd.setPixelRatio(Math.min(2,window.devicePixelRatio||1));
 host.innerHTML=''; host.appendChild(rnd.domElement);
 scene.add(new THREE.AmbientLight(0xffffff,.9));
 var dl=new THREE.DirectionalLight(0xffffff,.85); dl.position.set(3,6,6); scene.add(dl);
 var dl2=new THREE.DirectionalLight(0x8899ff,.28); dl2.position.set(-4,2,-4); scene.add(dl2);
 var g=new THREE.Group(); scene.add(g);
 var skin=new THREE.MeshStandardMaterial({color:0xb8a08a,roughness:.95});
 function cyl(rt,rb,h,seg,mat){ return new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,seg||22,1),mat); }
 function gtype(r,slot){ if(!r)return null; var t=(r.t||'').toLowerCase();
   if(slot==='hat'){ if(/beanie|watch ?cap|skully|knit hat/.test(t))return 'beanie'; if(/bucket/.test(t))return 'bucket'; return 'cap'; }
   if(slot==='top'){ if(/hood/.test(t)||r.c==='hoodie_sweat')return 'hood'; if(r.c==='tee'||/t-?shirt|\btee\b|s\/s|short ?sleeve|polo|tank|jersey/.test(t))return 'tee'; return 'ls'; }
   if(slot==='bottom'){ if(r.c==='shorts'||/(jorts?|shorts?)(?!\s*sleeve)/.test(t))return 'shorts'; return 'pants'; }
   return slot; }
 function armMesh(mat,side,frac,thick){ var len=1.8*frac; var m=cyl(thick,thick*.82,len,16,mat); m.position.set(side*1.02,2.62-len/2,0); m.rotation.z=side*0.12; return m; }
 function legMesh(mat,side,frac,thick){ var len=2.0*frac; var m=cyl(thick,thick*.8,len,18,mat); m.position.set(side*0.34,0.98-len/2,0); return m; }
 function torsoMesh(mat,rt,rb,h,y){ var m=cyl(rt,rb,h,30,mat); m.position.y=y; return m; }
 var head=new THREE.Mesh(new THREE.SphereGeometry(.5,28,28),skin); head.position.y=3.2; g.add(head);
 var neck=cyl(.17,.2,.32,16,skin); neck.position.y=2.86; g.add(neck);
 g.add(armMesh(skin,-1,1,.15)); g.add(armMesh(skin,1,1,.15));
 g.add(legMesh(skin,-1,1,.28)); g.add(legMesh(skin,1,1,.28));
 if(items.bottom){ var bm=_matFor(items.bottom); var bf=(gtype(items.bottom,'bottom')==='shorts')?0.5:1; g.add(legMesh(bm,-1,bf,.34)); g.add(legMesh(bm,1,bf,.34)); }
 if(items.top){ var tm=_matFor(items.top); var tt=gtype(items.top,'top'); g.add(torsoMesh(tm,.95,.77,2.0,1.75)); var sf=(tt==='tee')?0.42:1; g.add(armMesh(tm,-1,sf,.185)); g.add(armMesh(tm,1,sf,.185));
   if(tt==='hood'){ var hood=new THREE.Mesh(new THREE.SphereGeometry(.56,20,16,0,Math.PI*2,0,Math.PI*0.62),tm); hood.position.set(0,2.98,-.18); hood.rotation.x=-0.3; g.add(hood); } }
 if(items.layer){ var lm=_matFor(items.layer); g.add(torsoMesh(lm,1.07,.87,2.06,1.75)); g.add(armMesh(lm,-1,1,.205)); g.add(armMesh(lm,1,1,.205)); }
 if(items.hat){ var hm=_matFor(items.hat); var ht=gtype(items.hat,'hat');
   if(ht==='beanie'){ var be=new THREE.Mesh(new THREE.SphereGeometry(.56,22,18,0,Math.PI*2,0,Math.PI*0.6),hm); be.position.set(0,3.32,0); g.add(be); }
   else if(ht==='bucket'){ var bcr=cyl(.5,.6,.42,26,hm); bcr.position.y=3.55; g.add(bcr); var bbr=cyl(.62,.9,.22,26,hm); bbr.position.y=3.3; g.add(bbr); }
   else { var crown=cyl(.55,.57,.4,26,hm); crown.position.y=3.55; g.add(crown); var brim=new THREE.Mesh(new THREE.CylinderGeometry(.86,.86,.05,26),hm); brim.position.set(0,3.4,.32); brim.scale.z=1.3; g.add(brim); } }
 if(items.shoe){ var shm=_matFor(items.shoe); var fL=new THREE.Mesh(new THREE.BoxGeometry(.42,.26,.92),shm); fL.position.set(-.34,-1.16,.26); g.add(fL); var fR=new THREE.Mesh(new THREE.BoxGeometry(.42,.26,.92),shm); fR.position.set(.34,-1.16,.26); g.add(fR); }
 var sh=new THREE.Mesh(new THREE.CircleGeometry(1.25,32),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.32}));
 sh.rotation.x=-Math.PI/2; sh.position.y=-1.42; g.add(sh);
 g.position.y=-0.35;
 var drag=false,lx=0,auto=.005;
 host.addEventListener('pointerdown',function(e){drag=true;lx=e.clientX;host.style.cursor='grabbing';});
 window.addEventListener('pointerup',function(){drag=false;host.style.cursor='grab';});
 window.addEventListener('pointermove',function(e){ if(drag){ g.rotation.y+=(e.clientX-lx)*.011; lx=e.clientX; }});
 function loop(){ if(!_mq3d)return; if(!drag) g.rotation.y+=auto; rnd.render(scene,cam); _mq3d.raf=requestAnimationFrame(loop); }
 _mq3d={rnd:rnd,raf:0};
 loop();
 if(capEl){ var tot=SLOTORDER.filter(function(k){return items[k];}).reduce(function(a,k){return a+items[k].g;},0);
   capEl.innerHTML='A spinnable 3D fit — '+gbp(tot)+'. Drag to rotate. Built in each piece’s real colours; where the store allows it the product image maps on too.'; }
}
function renderPreview(){
 if(!_pvBase)return;
 if(_pvView==='body'){
  // interim: clean 2D "on a figure" view while the realistic AI try-on is being built
  // (the old primitive-3D render is retired \u2014 it read as warped/floating, not a worn look)
  cleanup3D(); $('pvslots').innerHTML=pvMannequin(_pvBase);
 } else { cleanup3D(); $('pvslots').innerHTML=pvPieces(_pvBase); }
 const bb=$('pvbody'); if(bb) bb.innerHTML = _pvView==='body' ? '\uD83D\uDCC7 Pieces' : '\uD83D\uDC64 On the body';
}
function openPreview(items,title,total){
 _pvBase=items; _pvView='pieces';
 $('pvtitle').textContent=title||'Outfit'; $('pvtotal').textContent=gbp(total||0);
 renderPreview(); $('pvwrap').hidden=false;
}
let _pvBase=null, _pvVars=[], _pvLocks={};
// remix: KEEP the locked pieces exactly, re-pick the unlocked ones so they COORDINATE with what's kept
function buildVariation(base, locks){
 const keep={}; SLOTORDER.forEach(k=>keep[k]=outfit[k]);
 SLOTORDER.forEach(k=>outfit[k]=null);
 // place the kept (locked) pieces first so re-picks harmonise around them
 SLOTORDER.forEach(k=>{ if(base[k] && locks[k]) outfit[k]=D.find(x=>x.u===base[k].u)||base[k]; });
 SLOTORDER.forEach(k=>{ if(base[k] && !locks[k]){ outfit[k]=coordPick(k,heroColour())||base[k]; } });
 const snap={}; SLOTORDER.forEach(k=>{ if(outfit[k]) snap[k]=outfit[k]; });
 SLOTORDER.forEach(k=>outfit[k]=keep[k]);
 return snap;
}
function genVariations(){
 _pvVars=[]; const seen=new Set(); const base=_pvBase;
 const anyChange=SLOTORDER.some(k=>base[k]&&!_pvLocks[k]);
 for(let t=0;t<20 && _pvVars.length<3;t++){
   const v=anyChange?buildVariation(base,_pvLocks):Object.assign({},base);
   const sig=SLOTORDER.map(k=>v[k]?v[k].u:'').join('|');
   if(seen.has(sig)){ if(!anyChange)break; continue; } seen.add(sig); _pvVars.push(v);
 }
 renderVariations();
}
function renderVariations(){
 const base=_pvBase;
 const ctrl=SLOTORDER.filter(k=>base[k]).map(k=>{const r=base[k], on=_pvLocks[k];
   return `<button class="varlock${on?' on':''}" data-varlock="${esc(k)}">`+
     `<span class="vlx">${on?'&#128274; keep':'&#8646; change'}</span>`+
     `<span class="vlk">${esc(k)}</span> &middot; ${esc(r.b)}</button>`;}).join('');
 const rows=_pvVars.map((v,i)=>{
   const tot=SLOTORDER.filter(k=>v[k]).reduce((a,k)=>a+v[k].g,0);
   const pcs=SLOTORDER.filter(k=>v[k]).map(k=>{const r=v[k], kept=_pvLocks[k];
     return `<div class="vpiece${kept?' lkd':''}"><img loading="lazy" src="${esc(r.i)}" onerror="this.style.opacity=.15">`+
       `<div class="vpt"><span class="vb">${esc(r.b)}</span>${esc(r.t.slice(0,22))}<span class="vg">${gbp(r.g)}</span></div></div>`;}).join('');
   return `<div class="varrow"><div class="varhd">Variation ${i+1} <b>${gbp(tot)}</b>`+
     `<button class="act sm" data-usevar="${i}">Use this</button></div><div class="varpcs">${pcs}</div></div>`;
 }).join('') || '<div class="empty">Lock fewer pieces \u2014 not enough left to vary.</div>';
 $('pvtitle').textContent='Variations';
 $('pvtotal').textContent='';
 $('pvslots').innerHTML=`<div class="varctrl"><div class="varctrlh">Tap a piece to keep or change it \u2014 the rest are rebuilt to match. &#128274; = kept.</div>`+
   `<div class="varlocks">${ctrl}</div><button class="act sm prim" id="pvregen">&#8646; New variations</button></div>`+rows;
}
function showVariations(){
 if(!_pvBase) return;
 _pvLocks={}; SLOTORDER.forEach(k=>{ if(_pvBase[k]) _pvLocks[k]=savedUrls.has(_pvBase[k].u); }); // liked kept by default
 genVariations();
}
document.addEventListener('click',e=>{
 const vl=e.target.closest('[data-varlock]');
 if(vl){ const k=vl.dataset.varlock; _pvLocks[k]=!_pvLocks[k]; genVariations(); return; }
 if(e.target.id==='pvregen'){ genVariations(); return; }
 const uv=e.target.closest('[data-usevar]');
 if(uv){ const v=_pvVars[+uv.dataset.usevar]; if(!v)return;
   outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
   SLOTORDER.forEach(k=>{ if(v[k]) outfit[k]=v[k]; });
   $('pvwrap').hidden=true; document.querySelector('.vt[data-v="fits"]').click(); setFitSub('build');
   initBuilder(); renderCanvas(); setSlot('top'); toast('Loaded that variation'); }
});
$('pvclose').onclick=()=>{cleanup3D();$('pvwrap').hidden=true;};
$('pvvary').onclick=showVariations;
{const bb=$('pvbody'); if(bb) bb.onclick=()=>{ _pvView=_pvView==='body'?'pieces':'body'; renderPreview(); };}
$('pvwrap').addEventListener('click',e=>{ if(e.target.id==='pvwrap')$('pvwrap').hidden=true; });
document.addEventListener('keydown',e=>{ if(e.key==='Escape')$('pvwrap').hidden=true; });
document.addEventListener('click',e=>{
 const pv=e.target.closest('[data-preview]');
 if(pv){ const f=FITS[+pv.dataset.preview]; if(f) openPreview(f.items,f.formula,fitTotal(f)); return; }
 const ps=e.target.closest('[data-preview-saved]');
 if(ps){ const f=savedFits[+ps.dataset.previewSaved]; if(f) openPreview(f.items,f.note,f.total); return; }
});
let _clrArm=false;
document.addEventListener('DOMContentLoaded',()=>{});
{const sc=$('savedclear'); if(sc) sc.onclick=()=>{
  if(!_clrArm){_clrArm=true; sc.textContent='Sure? Clear all'; setTimeout(()=>{_clrArm=false;sc.textContent='Clear all';},3000); return;}
  savedFits=[]; persistFits(); renderSaved(); toast('Saved outfits cleared'); };}
function setFitSub(which){
 document.querySelectorAll('.fsub').forEach(x=>x.classList.toggle('on',x.dataset.fs===which));
 $('buildmode').hidden=which!=='build';
 $('topmode').hidden=which!=='top';
 $('looksmode').hidden=which!=='looks';
 $('savedmode').hidden=which!=='saved';
 if(which==='build') initBuilder();
 else if(which==='top') renderTop();
 else if(which==='looks'){ if(!$('fitlist').innerHTML) renderFits(); }
 else if(which==='saved') renderSaved();
}
document.getElementById('fitsub').addEventListener('click',e=>{const b=e.target.closest('.fsub'); if(b) setFitSub(b.dataset.fs);});
{const hsf=$('hidesavedfits'); if(hsf) hsf.addEventListener('change',()=>{ if($('topmode')&&!$('topmode').hidden) renderTop(); else if($('looksmode')&&!$('looksmode').hidden) renderFits(); });}

$('viewtabs').onclick=e=>{const b=e.target.closest('.vt'); if(!b)return;
 document.querySelectorAll('.vt').forEach(x=>x.classList.remove('on')); b.classList.add('on');
 const v=b.dataset.v, isFits=v==='fits', isSurp=v==='surprise', isGrid=v==='grid';
 $('fits').hidden=!isFits; $('surprise').hidden=!isSurp; $('grid').hidden=!isGrid;
 $('more').style.display=isGrid?'':'none';
 $('loadmore').style.display='none'; if(isGrid) updateLoadMore();
 document.getElementById('chips').style.display=isGrid?'':'none';
 document.querySelector('.bar').style.display=isGrid?'':'none';
 if(isFits) setFitSub('build');
 if(isSurp) renderSurprise();
};
updateSavedCount();
$('htab').querySelector('tbody').innerHTML=ST.map(s=>{
 const ok=s.status==='ok';
 return `<tr><td>${esc(s.domain||'')}</td><td class="${ok?'st-ok':'st-bad'}">${esc(s.status||'')}</td>
 <td>${s.product_count??''}</td><td>${esc(String(s.note||s.platform||'').slice(0,150))}</td></tr>`;
}).join('');
render();
updateLoadMore();
saveStockState();
setTimeout(loadAllQuiet, 900);   // silently pull the whole library so every pool/count is complete
}
(function(){var GK='cat-gate-pw';
 if(!__ENC__){ var g0=document.getElementById('gate'); if(g0)g0.remove(); startApp(__PLAIN__, null); return; }
 var ov=document.getElementById('gate'),inp=document.getElementById('gpw'),btn=document.getElementById('gbtn'),err=document.getElementById('gerr');
 ov.hidden=false;
 function go(pw,fromSaved){ err.textContent=fromSaved?'':'Checking\u2026'; _unlock(pw).then(function(res){ try{localStorage.setItem(GK,pw);}catch(e){} ov.remove(); startApp(res.data, res.key); }).catch(function(){ try{localStorage.removeItem(GK);}catch(e){} if(!fromSaved){ err.textContent='Wrong password'; inp.value=''; } inp.focus(); }); }
 btn.onclick=function(){ if(inp.value) go(inp.value,false); };
 inp.addEventListener('keydown',function(e){ if(e.key==='Enter'&&inp.value) go(inp.value,false); });
 var saved=null; try{saved=localStorage.getItem(GK);}catch(e){}
 if(saved) go(saved,true); else inp.focus();
})();
</script></body></html>"""

pmax = int(max(prices)) if prices else 100
_pw = os.environ.get("SITE_PASSWORD","").strip()
_outdir = os.path.dirname(OUT) or "."
_chunk_files = []
if _pw:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _salt = os.urandom(16); _it = 200000
    _key = hashlib.pbkdf2_hmac("sha256", _pw.encode("utf-8"), _salt, _it, 32)
    _aes = AESGCM(_key)
    def _enc(js):
        n = os.urandom(12); ct = _aes.encrypt(n, js.encode("utf-8"), None)
        return base64.b64encode(n).decode(), base64.b64encode(ct).decode()
    _payload = '{"D":'+DATA+',"OUT":'+OUTJSON+',"ST":'+STATUS+'}'
    _iv0, _ct0 = _enc(_payload)
    ENCBLOB = json.dumps({"salt":base64.b64encode(_salt).decode(),"iv":_iv0,"ct":_ct0,"it":_it})
    PLAINDATA = "null"
    for _idx, _ch in enumerate(EXTRA, start=1):
        _cj = '{"D":'+json.dumps(_ch, separators=(",",":"), ensure_ascii=False)+'}'
        _iv, _ct = _enc(_cj)
        _fn = "chunk-%d.json" % _idx
        json.dump({"iv":_iv,"ct":_ct}, open(os.path.join(_outdir,_fn),"w"))
        _chunk_files.append(_fn)
    _gate_note = "ENCRYPTED \u2014 password gate ON, %d load-more chunk(s)" % len(EXTRA)
else:
    ENCBLOB = "null"
    PLAINDATA = '{"D":'+DATA+',"OUT":'+OUTJSON+',"ST":'+STATUS+'}'
    for _idx, _ch in enumerate(EXTRA, start=1):
        _fn = "chunk-%d.json" % _idx
        json.dump({"D":_ch}, open(os.path.join(_outdir,_fn),"w"))
        _chunk_files.append(_fn)
    _gate_note = "OPEN \u2014 no SITE_PASSWORD set, %d load-more chunk(s)" % len(EXTRA)
CHUNKSJSON = json.dumps(_chunk_files)
out = (tpl.replace("__ENCBLOB__", ENCBLOB).replace("__PLAINDATA__", PLAINDATA)
          .replace("__CHUNKSJSON__", CHUNKSJSON)
          .replace("__CATS__", CATJSON)
          .replace("__NROWS__", f"{len(rows):,}").replace("__NINSTOCK__", f"{instock:,}")
          .replace("__NBRANDS__", str(len(brands)))
          .replace("__NSTORE__", str(len({r["d"] for r in rows})))
          .replace("__PMAX__", str(pmax)).replace("__TITLE__", TITLE))
open(OUT,"w",encoding="utf-8").write(out)
import os as _os
_dir=_os.path.dirname(OUT) or "."
open(_os.path.join(_dir,"robots.txt"),"w").write("User-agent: *\nDisallow: /\n")

print(f"rows kept   : {len(rows):,}   in stock: {instock:,}   brands: {len(brands)}")
print(f"best-of     : {npend}")
print(f"from videos : {nvid}")
print(f"S-only flag : {sum(r['sm'] for r in rows)}")
print(f"restored favs: {sum(r['f'] for r in rows)}")
print(f"html        : {os.path.getsize(OUT)/1024:.0f} KB")
print(f"gate        : {_gate_note}\n")
for k, l in CATS:
    if cats[k]:
        print(f"  {l:22} {cats[k]:5}  ({sum(1 for r in rows if r['c']==k and r['a'])} in stock)")

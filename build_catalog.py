#!/usr/bin/env python3
"""Aggregate all scraped rows into one self-contained interactive HTML catalog."""
import json, glob, os, collections, re

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
        cat = o.get("category") or "other"
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
            "col": o.get("colour","unknown"),
            "neu": 1 if o.get("neutral") else 0,
            "nd": 1 if (o.get("new") or (o.get("domain") or "") in NEWDROP_DOMAINS) else 0,
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
keep, perdom = [], collections.Counter()
rows.sort(key=lambda r: (not (r["n"] or r["v"] or r["f"]), not r["a"], r["sm"], -(r["g"] or 0)))
for r in rows:
    if r["n"] or r["v"] or r["f"] or r["u"] in OUTFIT_URLS:
        keep.append(r); continue
    if r["d"] in REFERENCE_DOMAINS:
        keep.append(r); continue
    if not ALL_STOCK and (not r["a"] or r["sm"]):
        continue
    cap = FULL_CAP if r["d"] in FULL_DOMAINS else PER_DOMAIN
    if perdom[r["d"]] >= cap:
        continue
    perdom[r["d"]] += 1
    keep.append(r)
rows = keep

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

DATA   = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
STATUS = json.dumps(sorted(status.values(), key=lambda o: (o.get("status",""), o.get("domain",""))),
                    separators=(",", ":"), ensure_ascii=False)
CATJSON = json.dumps(CATS)
OUTJSON = json.dumps(OUTFITS, separators=(",",":"), ensure_ascii=False)

tpl = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
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
</style></head><body>
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
  <span class="vtsep"></span>
  <span id="collections" class="collrow"></span>
 </div>
 <div class="chips" id="chips"></div>
 <div class="bar">
  <input type="search" id="q" placeholder="Search title or brand&hellip;">
  <select id="brand"><option value="">All brands</option></select>
  <select id="sort"><option value="rel">Sort: brand</option><option value="pa">Price: low to high</option>
   <option value="pd">Price: high to low</option><option value="az">Name A&ndash;Z</option></select>
  <div class="rng">min&nbsp;£<span id="pvmin">0</span>
   <input type="range" id="pmin" min="0" max="600" value="0" step="5"></div>
  <div class="rng">max&nbsp;£<span id="pv">__PMAX__</span>
   <input type="range" id="pmax" min="0" max="__PMAX__" value="__PMAX__" step="5"></div>
  <label class="tog"><input type="checkbox" id="only" checked> in stock only</label>
  <label class="tog"><input type="checkbox" id="fitsme" checked> fits me (hide S&#8209;only)</label>
  <button class="act" id="copyfav">Copy saved list</button>
  <button class="act" id="dlfav">Download saved</button>
 </div>
</div></header>
<main class="wrap">
 <div class="grid" id="grid"></div>
 <div id="fits" hidden>
  <div class="fitsub" id="fitsub">
   <button class="fsub on" data-fs="build">Build a fit</button>
   <button class="fsub" data-fs="looks">Starter looks<span class="n" id="lookn"></span></button>
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
       <button class="act sm" id="bclear">Clear</button>
       <button class="act sm" id="bsave">Save fit</button>
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
     </div>
     <div class="pkgrid" id="pkgrid"></div>
     <button class="more" id="pkmore" hidden>Show more</button>
    </div>
   </div>
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
 </div>
 <div class="empty" id="empty" hidden>Nothing matches those filters.</div>
 <button class="more" id="more" hidden>Show more</button>
 <details class="health"><summary>Source health &mdash; which stores worked, which didn't</summary>
  <table id="htab"><thead><tr><th>Store</th><th>Status</th><th>Products</th><th>Note</th></tr></thead><tbody></tbody></table>
 </details>
</main>
<div id="toast"></div>
<script>
const D=__DATA__, CATS=__CATS__, ST=__STATUS__, OUT=__OUTFITS__;
const PAGE=120; let shown=PAGE, active=new Set(), showPend=false, showFav=false, showVid=false, showBW=false, showND=false;
const KEY='streetwear-catalog-saved-v1';
// Saves are keyed by product URL, not row id, so they survive rebuilds where ids shift.
// localStorage works when this file is opened locally; if a sandbox blocks it we fall
// back to memory and the Download button is the safety net.
let STORE_OK=true;
function loadSaved(){
 try{ const raw=localStorage.getItem(KEY); return raw? new Set(JSON.parse(raw)) : new Set(); }
 catch(e){ STORE_OK=false; return new Set(); }
}
function persist(){
 try{ localStorage.setItem(KEY, JSON.stringify([...savedUrls])); }
 catch(e){ STORE_OK=false; }
}
const savedUrls = loadSaved();
D.forEach(r=>{ if(r.f) savedUrls.add(r.u); });      // merge anything restored from disk
const favs=new Set(D.filter(r=>savedUrls.has(r.u)).map(r=>r.id));
persist();
const $=id=>document.getElementById(id);
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
  `<button class="chip nd" data-x="nd">&#9889; New Drops<span class="n">${D.filter(r=>r.nd).length}</span></button>`+
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

function filtered(){
 const q=$('q').value.trim().toLowerCase(), br=$('brand').value,
       pm=+$('pmax').value, pn=+$('pmin').value,
       only=$('only').checked, fits=$('fitsme').checked;
 let out=D.filter(r=>
   (!active.size||active.has(r.c)) && (!br||r.b===br) && (!only||r.a) &&
   (!fits||!r.sm) && (!showPend||r.n) && (!showVid||r.v) &&
   (!showFav||favs.has(r.id)) &&
   (!showND||r.nd) &&
   (!showBW||((r.c==='tee'||r.c==='longsleeve')&&(r.col==='black'||r.col==='white'))) &&
   r.g<=pm && r.g>=pn &&
   (!q||r.t.toLowerCase().includes(q)||r.b.toLowerCase().includes(q)));
 const s=$('sort').value;
 if(s==='pa')out=[...out].sort((a,b)=>a.g-b.g);
 else if(s==='pd')out=[...out].sort((a,b)=>b.g-a.g);
 else if(s==='az')out=[...out].sort((a,b)=>a.t.localeCompare(b.t));
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
 $('favcount').textContent=favs.size+' saved'; const fn=$('favn'); if(fn)fn.textContent=favs.size;
 $('empty').hidden=f.length>0;
 $('more').hidden=f.length<=shown;
 $('more').textContent=`Show more (${f.length-shown} left)`;
}
$('grid').addEventListener('click',e=>{
 const b=e.target.closest('[data-fav]'); if(!b)return;
 e.preventDefault();
 const id=+b.dataset.fav;
 const rec=D.find(x=>x.id===id);
 if(favs.has(id)){ favs.delete(id); if(rec) savedUrls.delete(rec.u); }
 else { favs.add(id); if(rec) savedUrls.add(rec.u); }
 persist();
 b.classList.toggle('on');
 $('favcount').textContent=favs.size+' saved'; $('favn').textContent=favs.size;
 if(showFav) render();
});
$('more').onclick=()=>{shown+=PAGE;render()};
$('pmin').addEventListener('input',e=>{$('pvmin').textContent=e.target.value;shown=PAGE;render()});
['q','brand','sort','only','fitsme'].forEach(id=>$(id).addEventListener('input',()=>{shown=PAGE;render()}));
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
const cvTotal=()=>Object.values(outfit).reduce((a,b)=>a+(b?b.g:0),0);

const locked={};
function renderCanvas(){
 $('cvslots').innerHTML=CVSLOTS.map(s=>{
  const r=outfit[s.k], act=s.k===activeSlot?' act':'', lk=locked[s.k]?' lk':'';
  if(r) return `<div class="cvslot filled${act}${lk}" data-slot="${s.k}">
    <button class="pin${locked[s.k]?' on':''}" data-lock="${s.k}" title="${locked[s.k]?'Locked — kept when filling':'Lock this piece'}">&#128204;</button>
    <button class="rm" data-rm="${s.k}" title="Remove">&times;</button>
    <div class="cvlab">${s.label}</div>
    <img src="${esc(r.i)}" alt="" onerror="this.remove()">
    <div class="cvm"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>
     <div class="pp">${gbp(r.g)} <a class="cvbuy" href="${esc(r.u)}" target="_blank" rel="noopener" data-buy>View &rarr;</a></div></div></div>`;
  return `<div class="cvslot empty${act}" data-slot="${s.k}">
    <div class="cvlab">${s.label}</div><div class="cvadd">+ choose</div></div>`;
 }).join('');
 $('btotal').textContent=gbp(cvTotal());
}
function pickerPool(){
 const s=CVSLOTS.find(x=>x.k===activeSlot);
 const q=$('pkq').value.trim().toLowerCase(), col=$('pkcol').value, fit=$('pkfit').checked;
 let out=[]; s.cats.forEach(c=>(byCat[c]||[]).forEach(r=>out.push(r)));
 out=out.filter(r=>r.a && r.i && (!fit||!r.sm) && (!col||r.col===col) &&
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
 const lk=e.target.closest('[data-lock]');
 if(lk){e.stopPropagation(); const k=lk.dataset.lock; locked[k]=!locked[k]; renderCanvas();
   toast(locked[k]?'Locked — kept when you fill or surprise':'Unlocked'); return;}
 const rm=e.target.closest('[data-rm]');
 if(rm){e.stopPropagation(); const k=rm.dataset.rm; outfit[k]=null; locked[k]=false; renderCanvas(); return;}
 const sl=e.target.closest('[data-slot]'); if(sl) setSlot(sl.dataset.slot);
});
$('pkgrid').addEventListener('click',e=>{
 const c=e.target.closest('[data-pick]'); if(!c)return;
 const r=D.find(x=>x.id===+c.dataset.pick); if(!r)return;
 outfit[activeSlot]=r; renderCanvas();
 const order=CVSLOTS.map(s=>s.k), ci=order.indexOf(activeSlot);
 const rot=order.slice(ci+1).concat(order.slice(0,ci+1));
 const nextEmpty=rot.find(k=>!outfit[k]);
 if(nextEmpty) setSlot(nextEmpty); else renderPicker();
});
['pkq','pkcol','pkfit'].forEach(id=>$(id).addEventListener('input',()=>{pkShown=60;renderPicker();}));
$('pkmore').onclick=()=>{pkShown+=60;renderPicker();};

// ---- grammar-aware selection ----
function rndFrom(cats,filt){
 let pool=[]; cats.forEach(c=>(byCat[c]||[]).forEach(r=>{if(r.a&&r.i&&!r.sm)pool.push(r);}));
 if(filt)pool=pool.filter(filt); if(!pool.length)return null;
 pool.sort((a,b)=>(b.f-a.f)||((b.n?1:0)-(a.n?1:0)));
 const head=pool.slice(0,Math.max(40,Math.floor(pool.length*0.35)));
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
 const c=catsOf(k);
 if(k==='top')   return rndFrom(c,r=>!r.neu)||rndFrom(c);
 if(k==='bottom')return rndFrom(c,r=>r.neu)||rndFrom(c);
 if(k==='hat')   return (hero&&rndFrom(c,r=>r.col===hero))||rndFrom(c,r=>r.neu)||rndFrom(c);
 if(k==='shoe')  return rndFrom(c,r=>r.neu||(hero&&r.col===hero))||rndFrom(c);
 if(k==='layer') return rndFrom(c,r=>r.neu)||rndFrom(c);
 return rndFrom(c);
}
// FILL THE REST: complete only the empty slots, coordinating with what's placed/pinned
$('bfill').onclick=()=>{
 let hero=heroColour();
 // if no top yet, place one first so the rest has something to coordinate to
 if(!outfit.top && !locked.top){ outfit.top=coordPick('top',null); hero=heroColour(); }
 let n=0;
 ['top','bottom','shoe','hat'].forEach(k=>{ if(!outfit[k] && !locked[k]){ outfit[k]=coordPick(k,hero); if(outfit[k])n++; }});
 renderCanvas(); setSlot('top');
 toast(n? `Filled ${n} slot${n>1?'s':''} around your picks` : 'Already complete — unlock or clear to change');
};
// SURPRISE ME: rebuild every UNLOCKED slot into a fresh coordinated fit
$('brandom').onclick=()=>{
 ['hat','layer','top','bottom','shoe','accessory'].forEach(k=>{ if(!locked[k]) outfit[k]=null; });
 if(!outfit.top) outfit.top=rndFrom(['longsleeve','tee','hoodie_sweat'],r=>!r.neu)||rndFrom(['longsleeve','tee']);
 const hero=heroColour();
 if(!locked.bottom) outfit.bottom=coordPick('bottom',hero);
 if(!locked.shoe)   outfit.shoe=coordPick('shoe',hero);
 if(!locked.hat)    outfit.hat=coordPick('hat',hero);
 renderCanvas(); setSlot('top'); toast('Fresh fit — lock the keepers, then Fill or Surprise again');
};
$('bclear').onclick=()=>{outfit={hat:null,layer:null,top:null,bottom:null,shoe:null,accessory:null};
 Object.keys(locked).forEach(k=>locked[k]=false); renderCanvas(); setSlot('top');};
$('bsave').onclick=()=>{
 let n=0; Object.values(outfit).forEach(r=>{if(r&&!savedUrls.has(r.u)){savedUrls.add(r.u);n++;const row=D.find(x=>x.u===r.u);if(row)favs.add(row.id);}});
 persist(); $('favcount').textContent=favs.size+' saved'; const fn=$('favn');if(fn)fn.textContent=favs.size;
 toast(n?`${n} pieces saved to your list`:'Nothing placed yet');
};
// ===== STARTER LOOKS (load into builder) =====
const FITS=OUT.map((o,i)=>({i,formula:o.formula,note:o.note,items:Object.assign({},o.items)}));
const fitTotal=f=>Object.values(f.items).reduce((a,b)=>a+b.g,0);
function slotHtml(r,k){
 return `<a class="slot" href="${esc(r.u)}" target="_blank" rel="noopener">
   <div class="lab">${k}</div><img loading="lazy" src="${esc(r.i)}" alt="">
   <div class="m"><div class="bb">${esc(r.b)}</div><div class="tt">${esc(r.t)}</div>
    <div class="pp">${gbp(r.g)}</div></div></a>`;
}
function fitHtml(f){
 const slots=SLOTORDER.filter(k=>f.items[k]).map(k=>slotHtml(f.items[k],k)).join('');
 return `<div class="fit" id="fit${f.i}">
   <div class="fh"><div><h3>${esc(f.formula)}</h3><div class="blurb">${esc(f.note)}</div></div>
    <div class="fr"><span class="cost">${gbp(fitTotal(f))}</span>
     <button class="act sm" data-use="${f.i}">Use &amp; edit</button></div></div>
   <div class="slots">${slots}</div></div>`;
}
function fitsFiltered(){
 const fm=$('fformula').value, bud=+$('fbudget').value, srt=$('fsort').value;
 let out=FITS.filter(f=>(!fm||f.formula===fm)&&fitTotal(f)<=bud);
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
function setFitSub(which){
 document.querySelectorAll('.fsub').forEach(x=>x.classList.toggle('on',x.dataset.fs===which));
 $('buildmode').hidden=which!=='build';
 $('looksmode').hidden=which!=='looks';
 if(which==='build') initBuilder();
 else if(!$('fitlist').innerHTML) renderFits();
}
document.getElementById('fitsub').addEventListener('click',e=>{const b=e.target.closest('.fsub'); if(b) setFitSub(b.dataset.fs);});

$('viewtabs').onclick=e=>{const b=e.target.closest('.vt'); if(!b)return;
 document.querySelectorAll('.vt').forEach(x=>x.classList.remove('on')); b.classList.add('on');
 const isFits=b.dataset.v==='fits';
 $('fits').hidden=!isFits; $('grid').hidden=isFits;
 $('more').style.display=isFits?'none':'';
 document.getElementById('chips').style.display=isFits?'none':'';
 document.querySelector('.bar').style.display=isFits?'none':'';
 if(isFits) setFitSub('build');
};
$('htab').querySelector('tbody').innerHTML=ST.map(s=>{
 const ok=s.status==='ok';
 return `<tr><td>${esc(s.domain||'')}</td><td class="${ok?'st-ok':'st-bad'}">${esc(s.status||'')}</td>
 <td>${s.product_count??''}</td><td>${esc(String(s.note||s.platform||'').slice(0,150))}</td></tr>`;
}).join('');
render();
</script></body></html>"""

pmax = int(max(prices)) if prices else 100
out = (tpl.replace("__DATA__", DATA).replace("__CATS__", CATJSON).replace("__STATUS__", STATUS)
          .replace("__NROWS__", f"{len(rows):,}").replace("__NINSTOCK__", f"{instock:,}")
          .replace("__NBRANDS__", str(len(brands)))
          .replace("__NSTORE__", str(len({r["d"] for r in rows})))
          .replace("__PMAX__", str(pmax)).replace("__TITLE__", TITLE)
          .replace("__OUTFITS__", OUTJSON))
open(OUT,"w",encoding="utf-8").write(out)

print(f"rows kept   : {len(rows):,}   in stock: {instock:,}   brands: {len(brands)}")
print(f"best-of     : {npend}")
print(f"from videos : {nvid}")
print(f"S-only flag : {sum(r['sm'] for r in rows)}")
print(f"restored favs: {sum(r['f'] for r in rows)}")
print(f"html        : {os.path.getsize(OUT)/1024:.0f} KB\n")
for k, l in CATS:
    if cats[k]:
        print(f"  {l:22} {cats[k]:5}  ({sum(1 for r in rows if r['c']==k and r['a'])} in stock)")

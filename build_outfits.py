#!/usr/bin/env python3
"""Curated outfit engine — the height of it.

Not randomised: every fit is assembled under an explicit styling rule (a "formula"),
coordinated by colour, and forced to MIX BRANDS so no look leans on a single label.
Draws on the whole catalogue — the scraped brands, the laced.com sneakers, the
Satoshi reference board and your saved pieces — and weights toward the best pieces:
your saves, curated Best-of picks, the brands you repeat-buy, and the pieces the
Black creators/rappers wore in the videos (BBM, EJWAYY, PappiiQ, DDG).

Styling grammar comes from the outfit accounts studied — @fitz2kickz (a matching cap
in every fit), @trendz4sportswear (shoe named first, set built around it), @arsnlnc
(loud graphic + short), @trendz — plus classic menswear rules (tonal, workwear,
monochrome). Each formula targets a different TYPE of outing so the set spans a wardrobe.
"""
import json, glob, random, collections, os, re

random.seed(11)   # deterministic — no Date/random drift between rebuilds

# Dave wears trainers/sneakers, loafers, Vans-type — never boots or dressy/"female" shoes.
BOOT_RE = re.compile(r"\bboots?\b|chukka|chelsea|combat|hiking|wellington|\bwellies?\b|desert boot|work ?boot|moc.?toe|\bmoccasin|timberland|red ?wing|blundstone|\bugg\b|tasman|tazz|slipper|danner|palladium|dr\.? ?martens|doc.? ?marten|gore.?tex boot|\bheel|stiletto|\bpumps?\b|ballet|mary.?jane|\bwedge|platform (heel|sandal)|oxford|thigh.?high|knee.?high|court shoe|brogue|derby shoe|monk strap", re.I)
# outfits lean on trainers/sneakers; loafers are a rare 1-in-many, other casual shoes occasional
SNEAKER_RE = re.compile(r"sneaker|trainer|\bdunk\b|air ?force|air ?max|air ?jordan|jordan \d|gel[- ]|\brunner|gazelle|samba|campus|superstar|\bforum\b|new balance|\bnb\b|\bvans\b|sk8|old ?skool|\bauthentic\b|\b\d{3,4}\b|\bmax\b|salomon|asics", re.I)
CASUAL_SHOE_RE = re.compile(r"sandal|slides?\b|slider|\bmule|\bclog|\bcroc", re.I)

# Title-first classifier — garment word beats brand/model (fixes 'Jordan thermal shirt' as a shoe).
_CLS_RULES = [
 ("headwear",  r"\b(caps?|hats?|beanies?|snapback|bucket ?hat|59fifty|5[- ]?panel|balaclava|do[- ]?rag|durag|visor|headband)\b"),
 ("underwear", r"\b(socks?|underwear|boxers?|briefs?)\b"),
 ("hoodie_sweat", r"\b(hoodie|hooded|sweat ?shirt|crew ?neck|crewneck|zip ?up|zip ?hood|pullover)\b"),
 ("longsleeve", r"\b(long ?sleeve|longsleeve|l/s|thermal|henley)\b"),
 ("jeans",     r"\b(jeans|denim pant|selvedge)\b"),
 ("sweats",    r"\b(sweat ?pants?|joggers?|track ?pants?|track ?jort)\b"),
 ("shorts",    r"\b(shorts|jorts?)\b"),
 ("pants",     r"\b(pants?|trousers?|chinos?|cargo|slacks|leggings?)\b"),
 ("windrunner",r"\b(windrunner|windbreaker|anorak|track ?jacket|track ?top|shell jacket)\b"),
 ("jacket_outerwear", r"\b(jackets?|coats?|parkas?|bomber|puffer|gilet|fleece|cardigan|overshirt|shacket|poncho|blazer(?! ?(low|mid|77)))\b"),
 ("footwear",  r"\b(sneakers?|trainers?|shoes?|footwear|dunk|air ?force|air ?max|air ?jordan|jordan \d|gel[- ]|slides?|sliders?|sandals?|loafers?|mules?|clogs?|crocs?|vans|sk8|old ?skool|runners?|gazelle|samba|campus|superstar|\bforum\b|new balance \d|\d{3,4}v\d)\b"),
 ("tee",       r"\b(t-?shirts?|tees?|s/s|short ?sleeve|jersey|polo)\b"),
 ("top",       r"\b(shirt|top|knit|sweater|button[- ]?up|button[- ]?down)\b"),
]
_CLS = [(k, re.compile(p, re.I)) for k, p in _CLS_RULES]
def classify(title, stored):
    t = title or ""
    for k, rx in _CLS:
        if rx.search(t):
            return k
    return stored

NEUTRALS = {"black","white","grey","cream","tan","brown","navy"}
HEROES   = {"red","blue","green","olive","burgundy","purple","orange","yellow","pink"}

# brands you repeat-save / rate, and the elevated streetwear labels worth foregrounding
FAV_BRANDS = {"lost intricacy","paraphernalia 97","cole buxton","icecream europe",
              "crysp denim","jjjjound","ebbets field flannels","eff","south of heaven®",
              "corteiz","huf","only ny","stussy","stüssy","polar skate co","butter goods",
              "by parra","brain dead","3sixteen","aries","maharishi","thisisneverthat",
              "reigning champ","gramicci","stan ray","new balance","asics","salomon",
              "satoshi nakamoto","kapital","needles","wtaps","cav empt","undercover",
              "aime leon dore","aimé leon dore","fear of god","essentials","rhude",
              "represent","carhartt wip","patta","palace","supreme","kith","noah",
              "our legacy","story mfg","kapital","sacai","bode","online ceramics"}

def load_urls(fn):
    s = set()
    if os.path.exists(fn):
        try:
            for x in json.load(open(fn)):
                u = x.get("url") if isinstance(x, dict) else x
                if u: s.add(u)
        except Exception:
            pass
    return s

favs = load_urls("favourites.json")
picks = load_urls("picks.json")
vidpicks = set()
if os.path.exists("video_picks.json"):
    try:
        for p in json.load(open("video_picks.json")):
            if p.get("url"): vidpicks.add(p["url"])
    except Exception:
        pass

TO_GBP = {"GBP":1.0,"USD":0.79,"EUR":0.85,"JPY":0.0052,"CNY":0.11,"KRW":0.00058,
 "AUD":0.52,"CAD":0.58,"NZD":0.47,"HKD":0.101,"SGD":0.59,"TWD":0.024,"DKK":0.114,
 "SEK":0.075,"NOK":0.073,"CHF":0.88,"PLN":0.20,"IDR":0.000048,"THB":0.023,
 "MXN":0.042,"BRL":0.14,"ZAR":0.043,"AED":0.215,"ILS":0.21,"INR":0.0094,"TRY":0.023}

# read the full catalogue: scraped rows PLUS the root snapshots (laced/satoshi/_saved)
files = sorted(glob.glob("rows/*.jsonl"))
for extra in sorted(glob.glob("*.jsonl")):
    if extra not in files: files.append(extra)

rows = []
for path in files:
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: o = json.loads(line)
        except Exception: continue
        if not o.get("available"):        continue
        if o.get("small_only"):           continue
        if not o.get("image") or not o.get("url"): continue
        try: p = float(o.get("price") or 0)
        except Exception: continue
        if p <= 0 or p >= 999999:         continue
        cur = (o.get("currency") or "USD").upper()
        g = p * TO_GBP.get(cur, 0.79)
        if g < 12 or g > 1200:            continue      # skip junk and blow-out grails
        sizes = [str(s).upper() for s in (o.get("sizes") or [])]
        big = (not sizes) or any(s in ("M","L","XL","XXL","2XL","3XL","MEDIUM","LARGE")
                                 or s.replace(".","").isdigit() for s in sizes)
        if not big: continue
        b = (o.get("brand") or "").strip()
        u = o["url"]
        title = o.get("title","")
        cat = classify(title, o.get("category"))
        if cat == "footwear" and BOOT_RE.search(title): continue
        score = 1
        if u in favs:            score += 6
        if u in picks:           score += 3
        if u in vidpicks:        score += 3
        if b.lower() in FAV_BRANDS: score += 2
        if cat == "footwear":                       # steer fills toward trainers/sneakers
            if "loafer" in title.lower():           score -= 8   # rare 1-in-many
            elif CASUAL_SHOE_RE.search(title):      score -= 4   # sandals/slides/mules occasional
            elif SNEAKER_RE.search(title):          score += 3
        rows.append({"b":b, "t":title, "c":cat,
                     "g":round(g,2), "p":round(p,2), "cur":cur,
                     "col":o.get("colour","unknown"), "neu":bool(o.get("neutral")),
                     "i":o["image"], "u":u, "sc":score, "s":sizes[:8]})

bycat = collections.defaultdict(list)
for r in rows: bycat[r["c"]].append(r)
for c in bycat: bycat[c].sort(key=lambda r: -r["sc"])

usage = collections.Counter()   # cap how often any one piece recurs, for variety

def pool(cats, colour=None, neutral=None, hero=False, limit=600):
    """Candidate pieces for one or more categories under colour/tone constraints."""
    if isinstance(cats, str): cats = [cats]
    out = []
    for cat in cats:
        for r in bycat.get(cat, [])[:5000]:
            if colour and r["col"] != colour:            continue
            if neutral is True and not r["neu"]:         continue
            if neutral is False and r["neu"]:            continue
            if hero and r["col"] not in HEROES:          continue
            out.append(r)
    return out[:limit]

def pick(cands, fit_urls, fit_brands, allow_same_brand=False):
    """Best coordinating piece: fresh brand, low recurrence, high curation score."""
    if not cands: return None
    poolc = [r for r in cands if r["u"] not in fit_urls]
    if not poolc: return None
    if not allow_same_brand:
        fresh = [r for r in poolc if r["b"].lower() not in fit_brands]
        if fresh: poolc = fresh
    # prefer rarely-used, then higher score; shuffle the head for variety
    poolc.sort(key=lambda r: (usage[r["u"]], -r["sc"]))
    head = poolc[:max(24, len(poolc)//4)]
    random.shuffle(head)
    return head[0] if head else None

outfits = []
seen = set()
def build(name, blurb, slots):
    """slots: list of (slotname, candidate_list). Brands are forced distinct."""
    fit, fit_urls, fit_brands = {}, set(), set()
    for slot, cands in slots:
        r = pick(cands, fit_urls, fit_brands)
        if r is None:
            # last resort: allow same brand rather than drop the whole fit
            r = pick(cands, fit_urls, fit_brands, allow_same_brand=True)
        if r is None:
            return None
        fit[slot] = r; fit_urls.add(r["u"]); fit_brands.add(r["b"].lower())
    sig = tuple(sorted(fit_urls))
    if sig in seen:
        return None
    seen.add(sig)
    for v in fit.values(): usage[v["u"]] += 1
    brands = {v["b"] for v in fit.values()}
    return {"formula": name, "note": blurb, "items": fit,
            "brands": len(brands),
            "total": round(sum(v["g"] for v in fit.values()), 2)}

def add(name, blurb, slotfn, n):
    made = 0
    for _ in range(n * 4):          # over-try; dedup/brand rules reject some
        o = build(name, blurb, slotfn())
        if o:
            outfits.append(o); made += 1
        if made >= n: break

TOPS   = ["longsleeve","tee","top","hoodie_sweat"]
LEGS   = ["jeans","pants","sweats","shorts"]

# ============ THE FORMULAS — each a different TYPE of outing ============

# 1) Cap Match — @fitz2kickz: a cap that mirrors the top, quiet legs
for colour in ("black","white","navy","green","red","blue","burgundy","brown","olive","cream","purple","orange","pink","tan","grey"):
    add("Cap Match",
        "Hat colour mirrors the top; bottom stays quiet so the pairing reads — @fitz2kickz runs a matching cap in every fit.",
        lambda c=colour: [("top", pool(["longsleeve","tee"], colour=c)),
             ("bottom", pool(["jeans","pants"], neutral=True)),
             ("shoe", pool("footwear")),
             ("hat", pool("headwear", colour=c))], 2)

# 2) Shoe-First Technical Set — @trendz4sportswear gorpcore
add("Shoe-First Technical Set",
    "Shoe chosen first, then a tonal technical set built around it — @trendz4sportswear names the trainer before the clothes.",
    lambda: [("shoe", pool("footwear")),
         ("layer", pool("windrunner")),
         ("bottom", pool("sweats", neutral=True)),
         ("top", pool(["tee","longsleeve"], neutral=True))], 16)

# 3) Heavy Graphic + Short — @arsnlnc summer statement
add("Heavy Graphic + Short",
    "Loud graphic up top, short underneath, clean shoe — @arsnlnc's core summer shape.",
    lambda: [("top", pool(["longsleeve","tee"], neutral=False)),
         ("bottom", pool("shorts", neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear", neutral=True))], 16)

# 4) Loud Top, Quiet Leg — the simplest rule in the grammar
add("Loud Top, Quiet Leg",
    "One hero colour up top, everything below it neutral. Hardest rule to get wrong.",
    lambda: [("top", pool(["longsleeve","hoodie_sweat","tee"], hero=True)),
         ("bottom", pool("jeans", neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear", neutral=True))], 16)

# 5) Windrunner Run — shell over LS with sweats
add("Windrunner Run",
    "Shell over a longsleeve with sweats — the shell the only loud piece.",
    lambda: [("layer", pool("windrunner")),
         ("top", pool("longsleeve", neutral=True)),
         ("bottom", pool("sweats", neutral=True)),
         ("shoe", pool("footwear"))], 14)

# 6) Tonal — single colour family head to toe, shoe breaks it
for colour in ("black","navy","olive","grey","brown","cream","tan"):
    add("Tonal",
        "One colour family head to toe, the shoe breaking it. Reads expensive whatever it cost.",
        lambda c=colour: [("top", pool(["hoodie_sweat","longsleeve"], colour=c)),
             ("bottom", pool(["sweats","pants"], colour=c)),
             ("shoe", pool("footwear")),
             ("hat", pool("headwear", colour=c))], 2)

# 7) All-Black Everything — the rapper monochrome (DDG / BBM)
add("All-Black Everything",
    "Blacked-out head to toe, one detail shoe. The monochrome rapper fit from the closet tours.",
    lambda: [("top", pool(["hoodie_sweat","longsleeve","tee"], colour="black")),
         ("bottom", pool(["jeans","sweats","pants"], colour="black")),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear", colour="black"))], 14)

# 8) Denim Focus — raw denim hero, plain tee, clean sneaker
add("Denim Focus",
    "Denim is the whole fit — a considered pair of jeans, plain tee, one clean sneaker.",
    lambda: [("top", pool(["tee","longsleeve"], neutral=True)),
         ("bottom", pool("jeans")),
         ("shoe", pool("footwear", neutral=True)),
         ("layer", pool("jacket_outerwear", neutral=True))], 14)

# 9) Tracksuit / Set — matching two-piece energy + runner
add("Tracksuit Energy",
    "Top-and-bottom in the same lane with a technical runner — the co-ord look done properly.",
    lambda: [("top", pool("hoodie_sweat", neutral=True)),
         ("bottom", pool("sweats", neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear", neutral=True))], 12)

# 10) Layered Winter — jacket over hoodie, heavier bottom, boot/runner
add("Layered Winter",
    "Outerwear over a hoodie with a heavier trouser — built for cold, styled in three tones.",
    lambda: [("layer", pool("jacket_outerwear")),
         ("top", pool("hoodie_sweat", neutral=True)),
         ("bottom", pool(["jeans","pants"], neutral=True)),
         ("shoe", pool("footwear"))], 14)

# 11) Clean Neutral — cream/tan minimalism
add("Clean Neutral",
    "Cream and tan, nothing loud — quiet luxury proportions, one warm sneaker.",
    lambda: [("top", pool(["longsleeve","hoodie_sweat","tee"], colour="cream")),
         ("bottom", pool(["pants","jeans"], neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear", neutral=True))], 10)

# 12) Statement Sneaker Anchor — neutral fit, one loud trainer
add("Statement Sneaker Anchor",
    "Everything quiet except the shoe — a hyped trainer carries the fit (the laced.com method).",
    lambda: [("shoe", pool("footwear", hero=True) or pool("footwear")),
         ("top", pool(["tee","longsleeve","hoodie_sweat"], neutral=True)),
         ("bottom", pool(["jeans","pants","sweats"], neutral=True)),
         ("hat", pool("headwear", neutral=True))], 14)

# 13) Workwear — chore/work jacket, utility trouser, boot or runner
add("Workwear",
    "Chore jacket, utility trouser, rugged shoe — Carhartt-lineage workwear built tonal.",
    lambda: [("layer", pool("jacket_outerwear", neutral=True)),
         ("top", pool(["longsleeve","tee"], neutral=True)),
         ("bottom", pool("pants", neutral=True)),
         ("shoe", pool("footwear"))], 12)

# 14) Longsleeve Layer — LS under a short-sleeve, your biggest lane
add("Longsleeve Layer",
    "Longsleeve under a tee with denim — the layering trick from your saves, longsleeves being half of them.",
    lambda: [("top", pool("longsleeve")),
         ("bottom", pool(["jeans","pants"], neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear"))], 12)

# 15) Summer Shorts & Tee — light, tonal, low
add("Summer Shorts & Tee",
    "Tee, shorts, low sneaker — the hottest-day fit kept tonal so it still looks considered.",
    lambda: [("top", pool("tee")),
         ("bottom", pool("shorts", neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear"))], 12)

# 16) Hoodie & Denim — the everyday default done right
add("Hoodie & Denim",
    "Heavyweight hoodie, good denim, one sneaker — the everyday uniform elevated by the pieces.",
    lambda: [("top", pool("hoodie_sweat")),
         ("bottom", pool("jeans", neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear", neutral=True))], 12)

# 17) Loud Shoe + Loud Top, tied by neutral leg — advanced two-accent
add("Two-Accent",
    "A loud top and a loud shoe tied together by a neutral leg — the harder, higher-level pairing.",
    lambda: [("top", pool(["longsleeve","tee","hoodie_sweat"], hero=True)),
         ("bottom", pool(["jeans","pants"], neutral=True)),
         ("shoe", pool("footwear", hero=True) or pool("footwear")),
         ("hat", pool("headwear", neutral=True))], 10)

# 18) Skate Fit — baggy bottom, graphic tee, skate shoe, cap
add("Skate Fit",
    "Baggy bottom, graphic tee, low skate shoe and a cap — the skate-shop uniform, kept cross-brand.",
    lambda: [("top", pool(["tee","longsleeve"], neutral=False)),
         ("bottom", pool(["jeans","pants"], neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear"))], 12)

# 19) Double Denim — done right, two washes, break with a knit/tee
add("Double Denim",
    "Two washes of denim tied together with a plain top and a clean sneaker — Canadian tuxedo, elevated.",
    lambda: [("layer", pool("jacket_outerwear")),
         ("top", pool(["tee","longsleeve"], neutral=True)),
         ("bottom", pool("jeans")),
         ("shoe", pool("footwear", neutral=True))], 10)

# 20) Smart Casual — loafers, trouser, fine knit
add("Smart Casual",
    "A loafer or clean low shoe with a trouser and a fine knit — dressed up without a suit.",
    lambda: [("top", pool(["longsleeve","top","hoodie_sweat"], neutral=True)),
         ("bottom", pool("pants", neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("layer", pool("jacket_outerwear", neutral=True))], 10)

# 21) Gorpcore Trail — shell, technical pant, trail-ready runner
add("Gorpcore Trail",
    "Technical shell, a utility trouser and a trail-ready runner — the outdoors look worn in the city.",
    lambda: [("layer", pool("windrunner")),
         ("top", pool(["longsleeve","tee"], neutral=True)),
         ("bottom", pool(["pants","sweats"], neutral=True)),
         ("shoe", pool("footwear"))], 12)

# 22) Monochrome White / Cream — the harder clean fit
add("Off-White Monochrome",
    "White and cream head to toe, one soft sneaker — the hardest colour to wear and the cleanest when it lands.",
    lambda: [("top", pool(["tee","longsleeve","hoodie_sweat"], colour="white") or pool(["tee","longsleeve"], colour="cream")),
         ("bottom", pool(["pants","jeans"], colour="cream") or pool("pants", neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear", neutral=True))], 8)

# 23) Vest Layer — vest/gilet over a longsleeve
add("Vest Layer",
    "A vest or gilet over a longsleeve with a straight trouser — the transitional-weather layer piece.",
    lambda: [("layer", pool("jacket_outerwear")),
         ("top", pool("longsleeve", neutral=True)),
         ("bottom", pool(["pants","jeans"], neutral=True)),
         ("shoe", pool("footwear"))], 10)

# 24) Statement Bottom — loud trouser, quiet everything else
add("Statement Bottom",
    "The trouser is the loud piece — everything above it neutral so the leg carries the fit.",
    lambda: [("bottom", pool(["pants","jeans","sweats"], hero=True) or pool(["pants","sweats"], neutral=False)),
         ("top", pool(["tee","longsleeve","hoodie_sweat"], neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear", neutral=True))], 10)

random.shuffle(outfits)
json.dump(outfits, open("outfits.json","w"), indent=1)

print(f"eligible products : {len(rows):,}")
print(f"outfits generated : {len(outfits)}")
c = collections.Counter(o["formula"] for o in outfits)
for k,v in c.most_common(): print(f"   {k:26} {v}")
multi = sum(1 for o in outfits if o["brands"] >= len(o["items"]))
print(f"\nall-distinct-brand fits : {multi}/{len(outfits)}")
if outfits:
    tot=[o["total"] for o in outfits]
    print(f"outfit cost range : GBP {min(tot):.0f} - {max(tot):.0f}   median {sorted(tot)[len(tot)//2]:.0f}")

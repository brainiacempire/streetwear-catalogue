#!/usr/bin/env python3
"""Generate outfits from the catalog using the styling grammar observed on the
flat-lay outfit accounts (@fitz2kickz, @trendz4sportswear, @arsnlnc).

The key structural finding from that research: those accounts publish every fit as an
explicit slot list — top / bottom / shoe / hat / layer — with a colour name per slot.
So that is exactly the data model used here.

Weighting follows Dave's 119 saved items: longsleeves are ~half his saves, then shorts,
then hats, and he repeat-saves Lost Intricacy, Paraphernalia 97, Cole Buxton, Icecream,
Crysp Denim, JJJJound, Ebbets and South of Heaven.
"""
import json, glob, random, collections

random.seed(11)   # deterministic — Date/random-free reproducible builds

NEUTRALS = {"black","white","grey","cream","tan","brown","navy"}
HEROES   = {"red","blue","green","olive","burgundy","purple","orange","yellow","pink"}

FAV_BRANDS = {"lost intricacy","paraphernalia 97","cole buxton","icecream europe",
              "crysp denim","jjjjound","ebbets field flannels","eff","south of heaven®",
              "corteiz","huf","only ny","stussy","polar skate co","butter goods",
              "by parra","brain dead","3sixteen","aries","maharishi","thisisneverthat",
              "reigning champ","gramicci","stan ray","new balance","asics","salomon"}

rows = []
favs = set()
try:
    for f in json.load(open("favourites.json")):
        u = f.get("url") if isinstance(f, dict) else f
        if u: favs.add(u)
except Exception:
    pass
picks = set()
try:
    for p in json.load(open("picks.json")):
        if p.get("url"): picks.add(p["url"])
except Exception:
    pass

TO_GBP = {"GBP":1.0,"USD":0.79,"EUR":0.85,"JPY":0.0052,"CNY":0.11,"KRW":0.00058,
 "AUD":0.52,"CAD":0.58,"NZD":0.47,"HKD":0.101,"SGD":0.59,"TWD":0.024,"DKK":0.114,
 "SEK":0.075,"NOK":0.073,"CHF":0.88,"PLN":0.20,"IDR":0.000048,"THB":0.023,
 "MXN":0.042,"BRL":0.14,"ZAR":0.043,"AED":0.215,"ILS":0.21,"INR":0.0094,"TRY":0.023}

for path in glob.glob("rows/*.jsonl"):
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
        if g < 12 or g > 900:             continue      # avoid junk and grails in generated fits
        sizes = [str(s).upper() for s in (o.get("sizes") or [])]
        # must be wearable: needs M or larger somewhere in the run, or be one-size
        big = (not sizes) or any(s in ("M","L","XL","XXL","2XL","3XL","MEDIUM","LARGE")
                                 or s.replace(".","").isdigit() for s in sizes)
        if not big: continue
        b = (o.get("brand") or "").strip()
        score = 0
        if o["url"] in favs:  score += 6
        if o["url"] in picks: score += 3
        if b.lower() in FAV_BRANDS: score += 2
        rows.append({"b":b, "t":o.get("title",""), "c":o.get("category"),
                     "g":round(g,2), "p":round(p,2), "cur":cur,
                     "col":o.get("colour","unknown"), "neu":bool(o.get("neutral")),
                     "i":o["image"], "u":o["url"], "sc":score, "s":sizes[:8]})

bycat = collections.defaultdict(list)
for r in rows: bycat[r["c"]].append(r)
for c in bycat: bycat[c].sort(key=lambda r: -r["sc"])

def pool(cat, colour=None, neutral=None, hero=None, limit=400):
    out = []
    for r in bycat.get(cat, [])[:4000]:
        if colour and r["col"] != colour: continue
        if neutral is True and not r["neu"]: continue
        if neutral is False and r["neu"]: continue
        if hero and r["col"] not in HEROES: continue
        out.append(r)
        if len(out) >= limit: break
    return out

def pick(lst, used):
    random.shuffle(lst[:120])
    for r in lst:
        if r["u"] not in used:
            return r
    return None

outfits = []
def build(name, blurb, slots, used):
    fit = {}
    for slot, cands in slots:
        r = pick(cands, used)
        if r is None:
            return None
        fit[slot] = r
        used.add(r["u"])
    return {"formula": name, "note": blurb, "items": fit,
            "total": round(sum(v["g"] for v in fit.values()), 2)}

TOPS_LOUD  = [c for c in ("longsleeve","tee","top") ]
seen_urls = set()

# ---- F8 Cap Match: hat colour mirrors the top, bottom stays quiet ----
for colour in ("black","white","navy","green","red","blue","burgundy","brown","grey","cream","olive","purple","orange","pink","tan"):
    for _ in range(3):
        o = build("Cap Match",
            "Hat colour mirrors the top; bottom stays quiet so the pairing reads. "
            "Straight from @fitz2kickz, who runs a matching cap in every single fit.",
            [("top",  pool("longsleeve", colour=colour) or pool("tee", colour=colour)),
             ("bottom", pool("jeans", neutral=True) or pool("pants", neutral=True)),
             ("shoe", pool("footwear")),
             ("hat",  pool("headwear", colour=colour))], seen_urls)
        if o: outfits.append(o)

# ---- F9 Shoe-First Technical Set: pick the shoe, build the set around it ----
for _ in range(22):
    o = build("Shoe-First Technical Set",
        "Shoe chosen first, then a tonal technical set built around it — the "
        "@trendz4sportswear method, where the caption names the trainer before the clothes.",
        [("shoe", pool("footwear")),
         ("layer", pool("windrunner")),
         ("bottom", pool("sweats", neutral=True)),
         ("top", pool("tee", neutral=True))], seen_urls)
    if o: outfits.append(o)

# ---- F10 Heavy Graphic + Short ----
for _ in range(22):
    o = build("Heavy Graphic + Short",
        "Loud graphic up top, short underneath, shoe picks up an accent from the print. "
        "@arsnlnc's core shape, and it matches your saves — shorts are your second-biggest lane.",
        [("top", pool("longsleeve", neutral=False) or pool("tee", neutral=False)),
         ("bottom", pool("shorts", neutral=True)),
         ("shoe", pool("footwear")),
         ("hat", pool("headwear", neutral=True))], seen_urls)
    if o: outfits.append(o)

# ---- F5 Loud Top / Quiet Leg ----
for _ in range(20):
    o = build("Loud Top, Quiet Leg",
        "One hero colour up top, everything below it neutral. The simplest rule in the "
        "grammar and the hardest to get wrong.",
        [("top", pool("longsleeve", hero=True) or pool("hoodie_sweat", hero=True)),
         ("bottom", pool("jeans", neutral=True)),
         ("shoe", pool("footwear", neutral=True)),
         ("hat", pool("headwear", neutral=True))], seen_urls)
    if o: outfits.append(o)

# ---- F7 Windrunner Run ----
for _ in range(18):
    o = build("Windrunner Run",
        "Shell over a longsleeve with sweats — the lane you asked to go deeper on, "
        "assembled so the shell is the only loud piece.",
        [("layer", pool("windrunner")),
         ("top", pool("longsleeve", neutral=True)),
         ("bottom", pool("sweats", neutral=True)),
         ("shoe", pool("footwear"))], seen_urls)
    if o: outfits.append(o)

# ---- F4 Tonal ----
for colour in ("black","navy","olive","grey","brown","cream"):
    for _ in range(2):
        o = build("Tonal",
            "Single colour family head to toe, with the shoe breaking it. Reads expensive "
            "regardless of what it cost.",
            [("top", pool("hoodie_sweat", colour=colour) or pool("longsleeve", colour=colour)),
             ("bottom", pool("sweats", colour=colour) or pool("pants", colour=colour)),
             ("shoe", pool("footwear", neutral=False) or pool("footwear")),
             ("hat", pool("headwear", colour=colour))], seen_urls)
        if o: outfits.append(o)

random.shuffle(outfits)
json.dump(outfits, open("outfits.json","w"), indent=1)

print(f"eligible products : {len(rows):,}")
print(f"outfits generated : {len(outfits)}")
c = collections.Counter(o["formula"] for o in outfits)
for k,v in c.most_common(): print(f"   {k:28} {v}")
tot=[o["total"] for o in outfits]
print(f"\noutfit cost range : £{min(tot):.0f} - £{max(tot):.0f}   median £{sorted(tot)[len(tot)//2]:.0f}")

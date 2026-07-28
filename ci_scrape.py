#!/usr/bin/env python3
"""CI scraper: pulls the core brands' live catalogs into rows/*.jsonl.
Runs in GitHub Actions on a schedule so the published catalogue self-updates.
Stdlib only (urllib) so CI needs no extra install beyond what's here."""
import json, os, time, urllib.request, urllib.error, datetime, re

BRANDS = json.load(open("brands.json"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
NOW = datetime.datetime.now(datetime.timezone.utc)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

WOMENS = re.compile(
    r"\bwom(?:e|a)n'?s?\b|\bwmns\b|\bladies\b|\blady\b|\bfemale\b|\bgirls?\b|\bfeminine\b"
    r"|\bbralette?s?\b|\bbralet(?:te)?s?\b|\bbandeau\b|\bcorsets?\b|\bbustiers?\b|\bcamisoles?\b|\bcami tops?\b"
    r"|\bbabydoll\b|\bnegligee\b|\blingerie\b|\bthongs?\b|\bpanties\b|\bknickers\b|\bgarter\b"
    r"|\bskirts?\b|\bskorts?\b|\bgowns?\b|\bpinafore\b|\bblouses?\b|\bpeplum\b|\bhalter\b|\btube ?top\b|\bbodysuits?\b"
    r"|\bbodycon\b|\bleotards?\b|\bcatsuits?\b|\bmaternity\b|\bnursing bra\b|legging|jeggings?"
    r"|\bmaxi ?dress\b|\bmini ?dress\b|\boff.?shoulder\b|\bcold.?shoulder\b|\bbackless\b|\bstrappy\b"
    r"|\bspaghetti.?strap\b|\bstilettos?\b|\bpeep.?toe\b|\bmary.?janes?\b|\bballet.?(?:flats?|pumps?)\b"
    r"|\bbras?\b|\blace\s+(?:tank|top|cami|bralette|dress|bodysuit|trim|slip)\b"
    r"|\bcrop(?:ped)?\s*(?:top|tee|t-?shirt|tank|cami|hoodie|sweat|jumper|knit)\b"
    r"|\bdress(?:es)?\b(?!\s*(?:shirts?|pants?|trousers?|chinos?|shorts?|shoes?|boots?|socks?|coats?|blazers?|jackets?|vests?|cardigans?|belts?|rings?|slacks?|watch|down|up|code|form|age|maker))"
    , re.I)
FLASHY = re.compile(
    r"\b(gucci|louis vuitton|\blvmh\b|prada|\bdior\b|balenciaga|fendi|versace|givenchy|burberry"
    r"|saint laurent|\bysl\b|celine|\bloewe\b|bottega|valentino|dolce ?& ?gabbana|dolce and gabbana"
    r"|giorgio armani|emporio armani|ferragamo|zegna|tom ford|moncler|canada goose|moose knuckles"
    r"|philipp plein|dsquared|\bamiri\b|balmain|off.?white|palm angels|golden goose|chrome hearts"
    r"|goyard|herm[eè]s|brunello|\bferrari\b|\bmclaren\b)\b", re.I)
KIDS = re.compile(
    r"\(gs\)|\(ps\)|\(td\)|\(ts\)|\bgs\b|\bgrade.?school\b|\bpre.?school\b|\btoddlers?\b|\binfants?\b"
    r"|\bbig kids?\b|\blittle kids?\b|\bgs sizing\b|^\s*kids?\b"
    , re.I)
# Women's-ONLY designer labels that leak via multi-brand retailers (Kith Women etc.).
WOMENS_BRAND = re.compile(
    r"\b(frankies bikinis|guizio|sandy liang|tropic of c|eb denim|asta resort|venuja|knwls"
    r"|studio amelia|conner ives|st\.? ?agni|mirror palais|house of sunny|nensi dojaka|poster girl"
    r"|di petsa|jade swim|susan fang|sinead gorey|sir the label|ottolinger|paloma wool"
    r"|gimaguas|realisation par|for love (?:&|and) lemons|are you am i)\b", re.I)
def clean_title(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"&(?:amp|nbsp|quot|apos|lt|gt|#\d+|#x[0-9a-fA-F]+);", " ", t)
    return re.sub(r"\s+", " ", t).strip()
# Gender from the item's OWN tags/type. Drop women-AND-not-men; keep men + unisex (dual-tagged).
_W_TAG = re.compile(r"\bwom[ae]n'?s?\b|\bladies\b|\bfemme\b|\bfemale\b|bvcategory:? ?women|gender[_:\- ]?wom|cat[- ]?wom|(^|[:/|])\s*women\b", re.I)
_M_TAG = re.compile(r"\bmen'?s?\b|\bhomme\b|\bmale\b|\bunisex\b|bvcategory:? ?men|gender[_:\- ]?men|cat[- ]?men|(^|[:/|])\s*men\b", re.I)
_TYPE_W = re.compile(r"(^|[:/|>])\s*wom[ae]n", re.I)
_TYPE_MU = re.compile(r"unisex|(^|[:/|>])\s*m[ae]n\b", re.I)
def women_item(ptype, tags):
    pt = str(ptype or "")
    if _TYPE_W.search(pt) and not _TYPE_MU.search(pt):
        return True
    blob = (pt + " " + " ".join(tags if isinstance(tags, list) else [str(tags or "")])).strip()
    return bool(blob) and bool(_W_TAG.search(blob)) and not bool(_M_TAG.search(blob))
def cat(title, ptype):
    t = (title + " " + (ptype or "")).lower()
    for k, pats in [("footwear","sneaker|shoe|trainer|boot|loafer|slide|dunk|jordan|gel-|samba"),
        ("headwear","\\bcaps?\\b(?! ?sleeve)|\\bhats?\\b|beanie|snapback|bucket|59fifty|trucker|ball ?cap"),
        ("hoodie_sweat","hoodie|hooded|sweatshirt|crewneck|zip.?up"),
        ("longsleeve","long.?sleeve|longsleeve|\\bls\\b|thermal|henley"),
        ("sweats","sweatpant|jogger|jogging ?bottom|track.?pant|fleece ?pant|nylon ?pant|tricot ?pant|parachute ?pant|warm.?up ?pant|lounge ?pant|active ?pant"),
        ("shorts","(?:jorts?|shorts?)(?!\\s*sleeve)"), ("jeans","jeans|denim"),
        ("windrunner","windbreaker|anorak|track.?jacket|fleece|half.?zip"),
        ("jacket_outerwear","jacket|coat|parka|bomber|puffer|vest"),
        ("pants","pants|trouser|cargo|chino"), ("tee","t.?shirt|tee\\b"),
        ("top","shirt|polo|jersey|tank|knit"), ("set","tracksuit|set\\b|two.?piece"),
        ("accessory","bag|belt|wallet|necklace|ring|chain|sock|hat|beanie")]:
        if re.search(pats, t): return k
    return "other"

os.makedirs("rows", exist_ok=True)
newdrops = set(); total = 0
status_rows = []                                  # per-brand health -> status.jsonl (feeds the on-site health table)
health = {"ok": 0, "thin": 0, "dead": 0}
for b in BRANDS:
    dom = b["domain"]; rows = []; saw_products = False
    try:
        for page in range(1, 21):   # max out full catalogues (up to 5000/brand; small brands early-exit)
            data = json.loads(get(f"https://{dom}/products.json?limit=250&page={page}"))
            prods = data.get("products", [])
            if not prods: break
            saw_products = True   # endpoint is alive and returning product (before men's filtering)
            for p in prods:
                title = clean_title(p.get("title",""))
                if not title: continue
                if WOMENS.search(title) or KIDS.search(title) or WOMENS_BRAND.search(title): continue
                if FLASHY.search(title) or FLASHY.search(str(p.get("vendor") or "")): continue   # big-designer/flashy flex
                _ptype = p.get("product_type")
                if women_item(_ptype, p.get("tags")): continue   # women's by its own tags/type
                variants = p.get("variants") or [{}]
                prices = [float(v.get("price") or 0) for v in variants if v.get("price")]
                if not prices: continue
                avail = any(v.get("available") for v in variants)
                sizes = [v.get("title") for v in variants if v.get("available") and v.get("title") not in (None,"Default Title")]
                img = (p.get("images") or [{}])[0].get("src","") if p.get("images") else ""
                created = p.get("published_at") or p.get("created_at") or ""
                is_new = False
                try:
                    dt = datetime.datetime.fromisoformat(created.replace("Z","+00:00"))
                    is_new = (NOW - dt).days <= 7
                except Exception: pass
                _tags=" ".join(p.get("tags") if isinstance(p.get("tags"),list) else [])
                colour="unknown"
                # word-boundary match (no "Stan"->tan / "shredded"->red substring hits), title before tags
                for _src in (title.lower(), _tags.lower()):
                    for cw in ["black","white","grey","gray","cream","tan","brown","navy","blue","green","olive","red","burgundy","pink","purple","orange","yellow"]:
                        if re.search(r"\b"+cw+r"\b", _src): colour={"gray":"grey"}.get(cw,cw); break
                    if colour!="unknown": break
                neutral=colour in ("black","white","grey","cream","tan","brown","navy")
                rows.append({"brand": b.get("brand") or p.get("vendor") or dom,
                    "domain": dom, "title": title, "category": cat(title, p.get("product_type")),
                    "price": min(prices), "currency": b.get("cur","USD"),
                    "available": avail, "sizes": sizes[:12], "image": img,
                    "url": f"https://{dom}/products/{p.get('handle','')}",
                    "tags": p.get("tags") if isinstance(p.get("tags"),list) else [],
                    "product_type": p.get("product_type") or "",
                    "colour": colour, "neutral": neutral, "new": is_new})
                if is_new and avail: newdrops.add(dom)
            if len(prods) < 250: break
            time.sleep(0.3)
        if rows:
            with open(f"rows/{dom}.jsonl","w") as fh:
                for r in rows: fh.write(json.dumps(r, ensure_ascii=False)+"\n")
            total += len(rows)
            print(f"  {dom}: {len(rows)}")
            _st = "ok" if len(rows) >= 5 else "thin"
            status_rows.append({"domain": dom, "brand": b.get("brand") or dom, "status": _st,
                "product_count": len(rows), "note": "" if _st == "ok" else "few pieces in stock"})
            health[_st] += 1
        else:
            # accurate health: a live endpoint whose product is all women's/kids/filtered is not the
            # same as a truly dead store — label it honestly so weekly curation targets the right ones.
            _note = "returned product but none were men's / in-filter" if saw_products else "no products returned"
            print(f"  {dom}: 0 ({'filtered' if saw_products else 'empty'})")
            status_rows.append({"domain": dom, "brand": b.get("brand") or dom, "status": "dead",
                "product_count": 0, "note": _note})
            health["dead"] += 1
    except Exception as e:
        print(f"  {dom}: skip ({type(e).__name__})")
        status_rows.append({"domain": dom, "brand": b.get("brand") or dom, "status": "dead",
            "product_count": 0, "note": type(e).__name__})
        health["dead"] += 1
    time.sleep(0.2)

json.dump(sorted(newdrops), open("newdrops.json","w"))
# ---- health report: written every run so the site + build log always show source health ----
with open("status.jsonl", "w", encoding="utf-8") as fh:
    for s in status_rows: fh.write(json.dumps(s, ensure_ascii=False) + "\n")
health["generated"] = NOW.isoformat(); health["rows"] = total; health["brands"] = len(BRANDS)
json.dump(health, open("brand_health.json", "w"), indent=1)
print(f"TOTAL {total} rows, {len(newdrops)} brands with drops this week")
print(f"HEALTH: {health['ok']} ok, {health['thin']} thin, {health['dead']} dead of {len(BRANDS)} brands")
_dead = [s["domain"] for s in status_rows if s["status"] == "dead"]
if _dead: print("  needs attention: " + ", ".join(sorted(_dead))[:600])

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

WOMENS = re.compile(r"\bwomen|\bwmns|\bladies|\bskirt\b|\bdress\b|\bbra\b|legging|bodysuit|\bgirls?\b|\bkids?\b|\bboys?\b|toddler|crop", re.I)
def cat(title, ptype):
    t = (title + " " + (ptype or "")).lower()
    for k, pats in [("footwear","sneaker|shoe|trainer|boot|loafer|slide|dunk|jordan|gel-|samba"),
        ("headwear","cap\\b|hat\\b|beanie|snapback|bucket|59fifty"),
        ("hoodie_sweat","hoodie|hooded|sweatshirt|crewneck|zip.?up"),
        ("longsleeve","long.?sleeve|longsleeve|\\bls\\b|thermal|henley"),
        ("sweats","sweatpant|jogger|track.?pant"),
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
for b in BRANDS:
    dom = b["domain"]; rows = []
    try:
        for page in range(1, 8):
            data = json.loads(get(f"https://{dom}/products.json?limit=250&page={page}"))
            prods = data.get("products", [])
            if not prods: break
            for p in prods:
                title = p.get("title","")
                if WOMENS.search(title): continue
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
                blob=(title+" "+" ".join(p.get("tags") if isinstance(p.get("tags"),list) else [])).lower()
                colour="unknown"
                for cw in ["black","white","grey","gray","cream","tan","brown","navy","blue","green","olive","red","burgundy","pink","purple","orange","yellow"]:
                    if cw in blob: colour={"gray":"grey"}.get(cw,cw); break
                neutral=colour in ("black","white","grey","cream","tan","brown","navy")
                rows.append({"brand": b.get("brand") or p.get("vendor") or dom,
                    "domain": dom, "title": title, "category": cat(title, p.get("product_type")),
                    "price": min(prices), "currency": b.get("cur","USD"),
                    "available": avail, "sizes": sizes[:12], "image": img,
                    "url": f"https://{dom}/products/{p.get('handle','')}",
                    "tags": p.get("tags") if isinstance(p.get("tags"),list) else [],
                    "colour": colour, "neutral": neutral, "new": is_new})
                if is_new and avail: newdrops.add(dom)
            if len(prods) < 250: break
            time.sleep(0.3)
        if rows:
            with open(f"rows/{dom}.jsonl","w") as fh:
                for r in rows: fh.write(json.dumps(r, ensure_ascii=False)+"\n")
            total += len(rows)
            print(f"  {dom}: {len(rows)}")
    except Exception as e:
        print(f"  {dom}: skip ({type(e).__name__})")
    time.sleep(0.2)

json.dump(sorted(newdrops), open("newdrops.json","w"))
print(f"TOTAL {total} rows, {len(newdrops)} brands with drops this week")

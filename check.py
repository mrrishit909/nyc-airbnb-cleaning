"""Step 5: the project's check. Recompute with different code, in plain Python straight from the five downloaded files (the csv, gzip, json and re modules, math and loops: no pandas, numpy or matplotlib): every count in the audit,
the field-by-field comparison of the two listings tables, the reviews against the listings, the outlines against the listings (a ray-casting point-in-polygon test of every listing against its own neighbourhood), the price quotes,
the stay lengths, the medians, quartiles and means, the price coverage and the registration counts.

    ./venv/bin/python check.py
"""
import csv
import gzip
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

csv.field_size_limit(10 ** 9)
HERE = Path(__file__).parent
D, R = HERE / "data", HERE / "results"
SHORT, LONG = "under 30 nights", "30 nights or more"
n_ok = 0


def same(label, got, want, rel=1e-9):
    global n_ok
    n_ok += 1
    want = float(want) if want not in ("", "nan") else float("nan")
    if math.isnan(want):
        assert math.isnan(got), f"{label}: recount {got} != results nan"
    else:
        assert abs(got - want) <= rel * max(1.0, abs(want)), f"{label}: recount {got} != results {want}"


def eq(label, got, want):
    global n_ok
    n_ok += 1
    assert got == want, f"{label}: recount {got!r} != results {want!r}"


def table(name):
    return list(csv.DictReader(open(R / f"{name}.csv")))


def rows(path, gz=False):
    f = gzip.open(path, "rt", encoding="utf-8", newline="") if gz else open(path, encoding="utf-8", newline="")
    return list(csv.DictReader(f))


def quantile(v, q):
    v = sorted(v); pos = (len(v) - 1) * q; lo = math.floor(pos); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def cents(text):
    return int(text.replace("$", "").replace(",", "").replace(".", ""))      # "$1,234.56" -> 123456


def num(text):
    return float(text) if text != "" else None


def ymd(text):
    return int(text.replace("-", ""))


def ring_has(x, y, ring):
    """does a horizontal ray from (x, y) cross the ring an odd number of times?"""
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def in_part(x, y, part):
    return sum(ring_has(x, y, ring) for ring in part) % 2 == 1                 # the outline, minus any holes


def main():
    L = rows(D / "listings.csv.gz", True); S = rows(D / "summary_listings.csv"); N = rows(D / "neighbourhoods.csv"); V = rows(D / "reviews.csv"); G = json.load(open(D / "neighbourhoods.geojson"))
    aud = {r["check"]: float(r["value"]) for r in table("audit")}
    def A(name, got):
        same(name, got, aud[name])

    # audit: rows, ids, the 296 listings only in the summary table
    A("rows: detailed listings", len(L)); A("rows: summary listings", len(S)); A("rows: neighbourhood list", len(N)); A("rows: neighbourhood outlines", len(G["features"])); A("rows: reviews", len(V)); A("columns: detailed listings", len(L[0])); A("columns: summary listings", len(S[0]))
    ids_l, ids_s = [r["id"] for r in L], [r["id"] for r in S]; a, b = set(ids_l), set(ids_s)
    A("duplicate ids: detailed", len(ids_l) - len(a)); A("duplicate ids: summary", len(ids_s) - len(b)); A("ids in both listings tables", len(a & b)); A("ids only in the detailed table", len(a - b)); A("ids only in the summary table", len(b - a))
    only = [r for r in S if r["id"] not in a]; review_ids = {r["listing_id"] for r in V}
    A("summary only: private rooms", sum(r["room_type"] == "Private room" for r in only)); A("summary only: with a price", sum(r["price"] != "" for r in only)); A("summary only: minimum stay under 30 nights", sum(r["minimum_nights"] != "" and float(r["minimum_nights"]) < 30 for r in only))
    A("summary only: with a registration field", sum(r["license"] != "" for r in only)); A("summary only: in Manhattan", sum(r["neighbourhood_group"] == "Manhattan" for r in only)); A("summary only: with reviews", sum(r["id"] in review_ids for r in only))
    scraped = {r["last_scraped"] for r in L}; A("scrape dates in the detailed table", len(scraped)); A("first scrape date", ymd(min(scraped))); A("last scrape date", ymd(max(scraped)))

    # audit: the price text and the two price columns
    text = [r["price"] for r in L if r["price"] != ""]; form = re.compile(r"\$\d{1,3}(,\d{3})*\.\d{2}")
    A("detailed prices written as text", len(text)); A("detailed prices not in the form $1,234.56", sum(not form.fullmatch(t) for t in text)); A("detailed prices blank", sum(r["price"] == "" for r in L)); A("detailed prices that fail to convert", 0)
    summ_price = {r["id"]: num(r["price"]) for r in S}; pairs = [(cents(r["price"]), summ_price[r["id"]]) for r in L if r["price"] != "" and summ_price[r["id"]] is not None]
    A("priced in both tables", len(pairs)); A("priced in one table only", sum((r["price"] != "") != (summ_price[r["id"]] is not None) for r in L))
    A("summary price equals the detailed price rounded half up to the dollar", sum((c + 50) // 100 == s for c, s in pairs)); A("largest difference between the two prices (dollars)", max(abs(c / 100 - s) for c, s in pairs))

    # audit: the registration field
    raw = [r["license"] for r in L if r["license"] != ""]; canon = [t.strip().upper() for t in raw]; numbers = [(t, c) for t, c in zip(raw, canon) if c != "EXEMPT"]; cnt = Counter(c for _, c in numbers)
    A("registration field: filled in (detailed)", len(raw)); A("registration field: Exempt", sum(c == "EXEMPT" for c in canon)); A("registration field: numbers", len(numbers)); A("registration numbers not in upper case or with spaces", sum(t != c for t, c in numbers))
    A("registration numbers not in the form OSE-STRREG-0000000", sum(not re.fullmatch(r"OSE-STRREG-\d{7}", c) for _, c in numbers)); A("distinct registration numbers", len(cnt)); A("registration numbers on more than one listing", sum(v > 1 for v in cnt.values()))
    A("listings sharing a registration number", sum(v for v in cnt.values() if v > 1)); A("most listings on one registration number", max(cnt.values()))
    A("minimum stay blank (summary)", sum(r["minimum_nights"] == "" for r in S)); A("longest minimum stay (nights)", max(float(r["minimum_nights"]) for r in S if r["minimum_nights"] != ""))
    bad = 0
    for r in S:
        if r["last_review"] != "":
            try:
                date.fromisoformat(r["last_review"])
            except ValueError:
                bad += 1
    A("last_review dates that fail to parse", bad)

    # combine (a): the two listings tables, field by field
    Sd = {r["id"]: r for r in S}
    def same_value(x, y):
        if x == "" or y == "":
            return x == y
        try:
            return float(x) == float(y)
        except ValueError:
            return x == y
    fields = [("room_type", "room_type"), ("minimum_nights", "minimum_nights"), ("number_of_reviews", "number_of_reviews"), ("last_review", "last_review"), ("license", "license"), ("neighbourhood_cleansed", "neighbourhood"), ("neighbourhood_group_cleansed", "neighbourhood_group"),
              ("host_id", "host_id"), ("latitude", "latitude"), ("longitude", "longitude"), ("availability_365", "availability_365"), ("calculated_host_listings_count", "calculated_host_listings_count"), ("reviews_per_month", "reviews_per_month"), ("number_of_reviews_ltm", "number_of_reviews_ltm")]
    for r in table("agreement"):
        fa, fb = [p for p in fields if p[0] == r["field"]][0]; both = [(x[fa], Sd[x["id"]][fb]) for x in L if x["id"] in Sd]; good = sum(same_value(p, q) for p, q in both)
        same(f"agreement {fa} compared", len(both), r["compared"]); same(f"agreement {fa} equal", good, r["equal"]); same(f"agreement {fa} different", len(both) - good, r["different"])

    # combine (b): the reviews against the listings
    per = Counter(r["listing_id"] for r in V); first, last = {}, {}
    for r in V:
        k, d = r["listing_id"], r["date"]
        if k not in first or d < first[k]:
            first[k] = d
        if k not in last or d > last[k]:
            last[k] = d
    A("reviews: earliest date", ymd(min(r["date"] for r in V))); A("reviews: latest date", ymd(max(r["date"] for r in V))); A("reviews: listings reviewed", len(per))
    A("reviews: reviewed listings missing from the summary table", len(set(per) - b)); A("reviews: reviewed listings missing from the detailed table", len(set(per) - a))
    A("listings whose number_of_reviews equals their review rows", sum(int(float(r["number_of_reviews"])) == per.get(r["id"], 0) for r in S))
    A("listings whose last_review equals their latest review (or both blank)", sum(r["last_review"] == last.get(r["id"], "") for r in S))
    A("detailed listings whose first_review equals their earliest review (or both blank)", sum(r["first_review"] == first.get(r["id"], "") for r in L)); A("listings with no review", sum(per.get(r["id"], 0) == 0 for r in S))
    yrs = Counter(int(r["date"][:4]) for r in V)
    for r in table("reviews_by_year"):
        same(f"reviews in {r['year']}", yrs[int(r["year"])], r["reviews"])

    # combine (c): the outlines against the listings
    parts, nfeat = {}, Counter()
    for f in G["features"]:
        k = (f["properties"]["neighbourhood_group"], f["properties"]["neighbourhood"]); g = f["geometry"]; ps = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        parts.setdefault(k, []).extend(ps); nfeat[k] += 1
    names = {(r["neighbourhood_group"], r["neighbourhood"]) for r in N}; used = {(r["neighbourhood_group"], r["neighbourhood"]) for r in S}
    A("neighbourhoods: names in the list", len(names)); A("neighbourhoods: names in the outlines", len(parts)); A("neighbourhoods: in the list but not the outlines", len(names - set(parts))); A("neighbourhoods: in the outlines but not the list", len(set(parts) - names))
    eq("split neighbourhoods", sorted((r["neighbourhood_group"], r["neighbourhood"], int(r["outlines"])) for r in table("split_neighbourhoods")), sorted((k[0], k[1], v) for k, v in nfeat.items() if v > 1))
    A("neighbourhoods drawn as two separate outlines", sum(v == 2 for v in nfeat.values())); A("neighbourhoods with no listing", len(names - used))
    box = {k: [(min(x for ring in p for x, _ in ring), max(x for ring in p for x, _ in ring), min(y for ring in p for _, y in ring), max(y for ring in p for _, y in ring)) for p in ps] for k, ps in parts.items()}
    ok = 0
    for r in S:
        k = (r["neighbourhood_group"], r["neighbourhood"]); x, y = float(r["longitude"]), float(r["latitude"])
        if k in parts and any(bx[0] <= x <= bx[1] and bx[2] <= y <= bx[3] and in_part(x, y, p) for bx, p in zip(box[k], parts[k])):
            ok += 1
    A("listings inside the outline of their own neighbourhood", ok); A("listings outside it", len(S) - ok); A("listings whose neighbourhood is not in the list", sum((r["neighbourhood_group"], r["neighbourhood"]) not in names for r in S))

    # the price quotes: what stay was priced
    q = [r for r in L if r["price_quote_checkin_date"] != ""]; qs = {SHORT: [], LONG: []}
    for r in q:
        nights = (date.fromisoformat(r["price_quote_checkout_date"]) - date.fromisoformat(r["price_quote_checkin_date"])).days; lead = (date.fromisoformat(r["price_quote_checkin_date"]) - date.fromisoformat(r["last_scraped"])).days
        mn = num(r["minimum_nights"]); qs[SHORT if (mn is not None and mn < 30) else LONG].append((nights, lead, mn is not None and nights == mn, r["price_quote_price_per_night"] != ""))
    for r in table("quote"):
        t = qs[r["stay"]]; nl = [x[0] for x in t]; ld = [x[1] for x in t]
        same("quotes", len(t), r["quotes"]); same("quotes priced", sum(x[3] for x in t), r["priced"]); same("quote nights min", min(nl), r["nights_min"]); same("quote nights median", quantile(nl, 0.5), r["nights_median"]); same("quote nights max", max(nl), r["nights_max"])
        same("quote equals minimum stay", sum(x[2] for x in t), r["quote_equals_minimum_stay"]); same("quote lead median", quantile(ld, 0.5), r["lead_days_median"]); same("quote lead max", max(ld), r["lead_days_max"])
    A("detailed listings with a price quote", len(q))
    qj = [(json.loads(r["price_quote_raw"])["quote"], SHORT if (num(r["minimum_nights"]) is not None and num(r["minimum_nights"]) < 30) else LONG) for r in q]; qc = {r["item"]: float(r["value"]) for r in table("quote_contents")}
    def fl(j, k):
        return float(j[k]) if j.get(k) is not None else None
    def QC(name, got):
        same("quote contents: " + name, got, qc[name])
    QC("quotes read", len(qj)); QC("quotes with a cleaning fee", sum(j.get("cleaning_fee") is not None for j, _ in qj)); QC("quotes with a service fee", sum(j.get("service_fee") is not None for j, _ in qj)); QC("quotes with taxes", sum(j.get("taxes") is not None for j, _ in qj))
    QC("quotes in US dollars", sum(j.get("currency") == "USD" for j, _ in qj)); QC("quotes with a discount", sum(fl(j, "discount_amount") is not None for j, _ in qj))
    QC("monthly-stay quotes with a discount", sum(fl(j, "discount_amount") is not None and s == LONG for j, s in qj)); QC("short-stay quotes with a discount", sum(fl(j, "discount_amount") is not None and s == SHORT for j, s in qj))
    pairs2 = [(fl(j, "total_price"), fl(j, "discounted_subtotal")) for j, _ in qj if fl(j, "total_price") is not None and fl(j, "discounted_subtotal") is not None]
    pn = [(fl(j, "total_price"), num(r["price_quote_price_per_night"]), (date.fromisoformat(r["price_quote_checkout_date"]) - date.fromisoformat(r["price_quote_checkin_date"])).days) for (j, _), r in zip(qj, q)]; pn = [x for x in pn if x[0] is not None and x[1] is not None]
    QC("quotes with a total and a price per night", len(pn)); QC("of which the total divided by the nights equals the price per night to the cent", sum(abs(t / nn - p) <= 0.006 for t, p, nn in pn))
    QC("quotes with both a total and a price after discount", len(pairs2)); QC("of which the two are within a dollar", sum(abs(t - s_) <= 1 for t, s_ in pairs2))
    sh = [fl(j, "discount_amount") / (fl(j, "discounted_subtotal") + fl(j, "discount_amount")) for j, s in qj if s == LONG and fl(j, "discount_amount") is not None and fl(j, "discounted_subtotal") is not None]
    QC("monthly-stay quotes with a discount and a price after it", len(sh)); QC("their discount as a share of the price before it: median", quantile(sh, 0.5)); QC("their discount as a share of the price before it: first quartile", quantile(sh, 0.25)); QC("their discount as a share of the price before it: third quartile", quantile(sh, 0.75))
    tol = 0
    for r in q:
        pq, p = r["price_quote_price_per_night"], r["price"]
        tol += pq == "" or p == "" or abs(round(float(pq), 2) - cents(p) / 100) <= 0.011
    A("quoted price per night equals the price (where both)", tol)

    # explore: stay length, price, registration, on the full list (the summary table)
    stay = lambda r: "unknown" if r["minimum_nights"] == "" else SHORT if float(r["minimum_nights"]) < 30 else LONG
    bins = [("1 night", 1, 1), ("2 nights", 2, 2), ("3 to 6 nights", 3, 6), ("7 to 29 nights", 7, 29), ("30 nights exactly", 30, 30), ("31 nights or more", 31, 10 ** 9)]
    for r, (nm, lo, hi) in zip(table("stay"), bins):
        n = sum(r_["minimum_nights"] != "" and lo <= float(r_["minimum_nights"]) <= hi for r_ in S); eq("stay name", r["stay_length"], nm); same(f"stay {nm}", n, r["listings"]); same(f"stay share {nm}", n / len(S), r["share"])
    groups = {("all", "All listings"): lambda r: True, **{("borough", bn): (lambda bn: lambda r: r["neighbourhood_group"] == bn)(bn) for bn in ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island")},
              **{("room_type", rt): (lambda rt: lambda r: r["room_type"] == rt)(rt) for rt in ("Entire home/apt", "Private room", "Hotel room", "Shared room")}}
    for r in table("price"):
        t = [x for x in S if groups[(r["group_type"], r["group"])](x) and (r["stay"] == "all" or stay(x) == r["stay"])]; p = [float(x["price"]) for x in t if x["price"] != ""]
        same("price listings", len(t), r["listings"]); same("price priced", len(p), r["priced"]); same("price median", quantile(p, 0.5), r["median"]); same("price q1", quantile(p, 0.25), r["q1"]); same("price q3", quantile(p, 0.75), r["q3"]); same("price mean", math.fsum(p) / len(p), r["mean"])
    for r in table("price_coverage"):
        t = [x for x in S if (float(x["availability_365"]) == 0) == r["availability_365"].startswith("none")]; same("coverage listings", len(t), r["listings"]); same("coverage priced", sum(x["price"] != "" for x in t), r["priced"]); same("coverage share", sum(x["price"] != "" for x in t) / len(t), r["share_priced"])
    def reg(r):
        return "none" if r["license"] == "" else "exempt" if r["license"].strip().upper() == "EXEMPT" else "number"
    for r in table("registration"):
        t = [x for x in S if stay(x) == r["stay"]]; same("registration listings", len(t), r["listings"])
        for k in ("number", "exempt", "none"):
            same(f"registration {k}", sum(reg(x) == k for x in t), r[k])
    sm = {r["key"]: float(r["value"]) for r in table("summary")}; pr = [float(x["price"]) for x in S if x["price"] != ""]
    for k, got in (("listings", len(S)), ("short_stay", sum(stay(x) == SHORT for x in S)), ("monthly_stay", sum(stay(x) == LONG for x in S)), ("stay_unknown", sum(stay(x) == "unknown" for x in S)), ("exactly_30", sum(x["minimum_nights"] != "" and float(x["minimum_nights"]) == 30 for x in S)),
                   ("private_rooms", sum(x["room_type"] == "Private room" for x in S)), ("entire_homes", sum(x["room_type"] == "Entire home/apt" for x in S)), ("priced", len(pr)), ("price_mean", math.fsum(pr) / len(pr)), ("price_median", quantile(pr, 0.5)), ("price_max", max(pr)),
                   ("priced_over_5000", sum(v > 5000 for v in pr)), ("priced_over_1000", sum(v > 1000 for v in pr)), ("price_p99", quantile(pr, 0.99))):
        same(f"summary {k}", got, sm[k])
    print(f"check.py: {n_ok} recomputed numbers agree with results/ (every count, comparison, outline test and statistic written out in plain Python)")


if __name__ == "__main__":
    main()

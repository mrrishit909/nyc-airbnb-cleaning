"""Steps 2-4: audit and clean the five tables, combine them, and ask what a night in New York costs.

    ./venv/bin/python analyze.py
        -> results/audit.csv  agreement.csv  split_neighbourhoods.csv  quote.csv  quote_contents.csv  reviews_by_year.csv  stay.csv  price.csv  price_coverage.csv  registration.csv  summary.csv

Tables: the detailed listings (30,259, with the price as text like "$1,250.00"), the summary listings (30,555, price in whole dollars), the neighbourhood list and outlines, and the reviews (one row per review).
Cleaning: prices are text and are turned into numbers; registration numbers are trimmed and put in upper case; dates are parsed. The summary table holds every listing in the detailed one, so it is the full list: one row per listing,
30,555 rows, with the price in whole dollars (checked against the cleaned detailed price). A "short stay" is a minimum stay under 30 nights, a "monthly stay" one of 30 nights or more. A listing has a price only if one was quoted
for it; the quote is for one particular stay, and the price is that quote divided by its nights. Medians and quartiles use linear interpolation between the sorted values.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as Poly

HERE = Path(__file__).parent
D, R = HERE / "data", HERE / "results"
PRICE_TEXT = r"^\$\d{1,3}(,\d{3})*\.\d{2}$"
LICENSE_FORM = r"^OSE-STRREG-\d{7}$"
BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
STAY = [("1 night", 1, 1), ("2 nights", 2, 2), ("3 to 6 nights", 3, 6), ("7 to 29 nights", 7, 29), ("30 nights exactly", 30, 30), ("31 nights or more", 31, 10 ** 9)]
SHORT, LONG = "under 30 nights", "30 nights or more"


def stats(v):
    v = np.asarray(v, float)
    return {"median": float(np.median(v)), "q1": float(np.quantile(v, 0.25)), "q3": float(np.quantile(v, 0.75)), "mean": float(v.mean())} if len(v) else {"median": np.nan, "q1": np.nan, "q3": np.nan, "mean": np.nan}


def inside(parts, pts):
    out = np.zeros(len(pts), bool)
    for part in parts:                                   # a part is a list of rings: the outline, then any holes (the even-odd rule handles both)
        crossings = np.zeros(len(pts), int)
        for ring in part:
            crossings += Poly(np.array(ring)).contains_points(pts)
        out |= crossings % 2 == 1
    return out


def main():
    R.mkdir(exist_ok=True)
    L = pd.read_csv(D / "listings.csv.gz", low_memory=False); S = pd.read_csv(D / "summary_listings.csv"); N = pd.read_csv(D / "neighbourhoods.csv"); V = pd.read_csv(D / "reviews.csv"); G = json.load(open(D / "neighbourhoods.geojson"))
    audit = []
    def add(name, value):
        audit.append((name, value))

    # Step 2: audit and clean
    add("rows: detailed listings", len(L)); add("rows: summary listings", len(S)); add("rows: neighbourhood list", len(N)); add("rows: neighbourhood outlines", len(G["features"])); add("rows: reviews", len(V)); add("columns: detailed listings", L.shape[1]); add("columns: summary listings", S.shape[1])
    add("duplicate ids: detailed", int(L["id"].duplicated().sum())); add("duplicate ids: summary", int(S["id"].duplicated().sum()))
    a, b = set(L["id"]), set(S["id"]); only_s = S[~S["id"].isin(a)]
    add("ids in both listings tables", len(a & b)); add("ids only in the detailed table", len(a - b)); add("ids only in the summary table", len(b - a))
    add("summary only: private rooms", int((only_s["room_type"] == "Private room").sum())); add("summary only: with a price", int(only_s["price"].notna().sum())); add("summary only: minimum stay under 30 nights", int((only_s["minimum_nights"] < 30).sum()))
    add("summary only: with a registration field", int(only_s["license"].notna().sum())); add("summary only: in Manhattan", int((only_s["neighbourhood_group"] == "Manhattan").sum())); add("summary only: with reviews", int(only_s["id"].isin(set(V["listing_id"])).sum()))
    add("scrape dates in the detailed table", int(L["last_scraped"].nunique())); add("first scrape date", int(L["last_scraped"].min().replace("-", ""))); add("last scrape date", int(L["last_scraped"].max().replace("-", "")))
    txt = L["price"].dropna().astype(str); L["price_clean"] = pd.to_numeric(L["price"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    add("detailed prices written as text", len(txt)); add("detailed prices not in the form $1,234.56", int((~txt.str.match(PRICE_TEXT)).sum())); add("detailed prices blank", int(L["price"].isna().sum())); add("detailed prices that fail to convert", int((L["price_clean"].isna() & L["price"].notna()).sum()))
    m = L.merge(S, on="id", suffixes=("_d", "_s")); both = m["price_clean"].notna() & m["price_s"].notna(); diff = (m.loc[both, "price_clean"] - m.loc[both, "price_s"]).abs()
    add("priced in both tables", int(both.sum())); add("priced in one table only", int((m["price_clean"].notna() ^ m["price_s"].notna()).sum())); add("summary price equals the detailed price rounded half up to the dollar", int((np.floor(m.loc[both, "price_clean"] + 0.5) == m.loc[both, "price_s"]).sum()))
    add("largest difference between the two prices (dollars)", float(diff.max()))
    raw = L["license"].dropna(); canon = raw.str.strip().str.upper(); regno = canon[canon != "EXEMPT"]
    add("registration field: filled in (detailed)", len(raw)); add("registration field: Exempt", int((canon == "EXEMPT").sum())); add("registration field: numbers", len(regno)); add("registration numbers not in upper case or with spaces", int((raw[canon != "EXEMPT"] != regno).sum()))
    add("registration numbers not in the form OSE-STRREG-0000000", int((~regno.str.match(LICENSE_FORM)).sum())); add("distinct registration numbers", int(regno.nunique())); vc = regno.value_counts()
    add("registration numbers on more than one listing", int((vc > 1).sum())); add("listings sharing a registration number", int(vc[vc > 1].sum())); add("most listings on one registration number", int(vc.max()))
    add("minimum stay blank (summary)", int(S["minimum_nights"].isna().sum())); add("longest minimum stay (nights)", int(S["minimum_nights"].max()))
    add("last_review dates that fail to parse", int((pd.to_datetime(S["last_review"], errors="coerce").isna() & S["last_review"].notna()).sum()))
    add("coordinates outside the latitude and longitude range of the outlines", 0)  # replaced below once the outlines are read

    # Step 3: combine. (a) the two listings tables, field by field, on the ids they share
    pairs = [("room_type", "room_type"), ("minimum_nights", "minimum_nights"), ("number_of_reviews", "number_of_reviews"), ("last_review", "last_review"), ("license", "license"), ("neighbourhood_cleansed", "neighbourhood_s"), ("neighbourhood_group_cleansed", "neighbourhood_group"),
             ("host_id", "host_id"), ("latitude", "latitude"), ("longitude", "longitude"), ("availability_365", "availability_365"), ("calculated_host_listings_count", "calculated_host_listings_count"), ("reviews_per_month", "reviews_per_month"), ("number_of_reviews_ltm", "number_of_reviews_ltm")]
    S2 = S.add_suffix("_s").rename(columns={"id_s": "id"}); mm = L.merge(S2, on="id"); agree = []
    for fa, fb in pairs:
        x, y = mm[fa], mm[fb + "_s" if fb + "_s" in mm.columns else fb]; eq = (x == y) | (x.isna() & y.isna())
        agree.append({"field": fa, "compared": len(mm), "equal": int(eq.sum()), "different": int((~eq).sum())})
    pd.DataFrame(agree).to_csv(R / "agreement.csv", index=False)

    # (b) the reviews against the listings
    V["d"] = pd.to_datetime(V["date"]); g = V.groupby("listing_id")["d"].agg(["size", "min", "max"]); full = S.set_index("id").join(g, how="left"); full["size"] = full["size"].fillna(0).astype(int)
    add("reviews: earliest date", int(V["d"].min().strftime("%Y%m%d"))); add("reviews: latest date", int(V["d"].max().strftime("%Y%m%d"))); add("reviews: listings reviewed", int(V["listing_id"].nunique()))
    add("reviews: reviewed listings missing from the summary table", len(set(V["listing_id"]) - b)); add("reviews: reviewed listings missing from the detailed table", len(set(V["listing_id"]) - a))
    add("listings whose number_of_reviews equals their review rows", int((full["number_of_reviews"] == full["size"]).sum()))
    lr = pd.to_datetime(full["last_review"]); add("listings whose last_review equals their latest review (or both blank)", int(((lr == full["max"]) | (lr.isna() & full["max"].isna())).sum()))
    fl = L.set_index("id").join(g, how="left"); fr = pd.to_datetime(fl["first_review"]); add("detailed listings whose first_review equals their earliest review (or both blank)", int(((fr == fl["min"]) | (fr.isna() & fl["min"].isna())).sum()))
    add("listings with no review", int((full["size"] == 0).sum()))
    pd.DataFrame({"year": sorted(V["d"].dt.year.unique())}).assign(reviews=lambda t: [int((V["d"].dt.year == y).sum()) for y in t["year"]]).to_csv(R / "reviews_by_year.csv", index=False)

    # (c) the outlines against the listings: is each listing inside the outline of its own neighbourhood?
    polys, nfeat = {}, {}
    for f in G["features"]:
        k = (f["properties"]["neighbourhood_group"], f["properties"]["neighbourhood"]); gm = f["geometry"]; parts = gm["coordinates"] if gm["type"] == "MultiPolygon" else [gm["coordinates"]]
        polys.setdefault(k, []).extend(parts); nfeat[k] = nfeat.get(k, 0) + 1
    names = set(map(tuple, N[["neighbourhood_group", "neighbourhood"]].values))
    add("neighbourhoods: names in the list", len(names)); add("neighbourhoods: names in the outlines", len(polys)); add("neighbourhoods: in the list but not the outlines", len(names - set(polys))); add("neighbourhoods: in the outlines but not the list", len(set(polys) - names))
    pd.DataFrame([{"neighbourhood_group": k[0], "neighbourhood": k[1], "outlines": v} for k, v in sorted(nfeat.items()) if v > 1]).to_csv(R / "split_neighbourhoods.csv", index=False)
    add("neighbourhoods drawn as two separate outlines", sum(v == 2 for v in nfeat.values())); add("neighbourhoods with no listing", len(names - set(map(tuple, S[["neighbourhood_group", "neighbourhood"]].values))))
    pts = np.c_[S["longitude"], S["latitude"]]; ok = np.zeros(len(S), bool)
    for k, parts in polys.items():
        idx = np.flatnonzero(((S["neighbourhood_group"] == k[0]) & (S["neighbourhood"] == k[1])).to_numpy())
        if len(idx):
            ok[idx] = inside(parts, pts[idx])
    add("listings inside the outline of their own neighbourhood", int(ok.sum())); add("listings outside it", int((~ok).sum())); add("listings whose neighbourhood is not in the list", int((~S.set_index(["neighbourhood_group", "neighbourhood"]).index.isin(names)).sum()))
    audit = [x for x in audit if x[0] != "coordinates outside the latitude and longitude range of the outlines"]

    # the price quote: what stay was priced
    q = L[L["price_quote_checkin_date"].notna()].copy(); q["nights"] = (pd.to_datetime(q["price_quote_checkout_date"]) - pd.to_datetime(q["price_quote_checkin_date"])).dt.days
    q["lead"] = (pd.to_datetime(q["price_quote_checkin_date"]) - pd.to_datetime(q["last_scraped"])).dt.days; q["stay"] = np.where(q["minimum_nights"] < 30, SHORT, LONG)
    qrows = [{"stay": s, "quotes": len(t), "priced": int(t["price_quote_price_per_night"].notna().sum()), "nights_min": int(t["nights"].min()), "nights_median": float(t["nights"].median()), "nights_max": int(t["nights"].max()),
              "quote_equals_minimum_stay": int((t["nights"] == t["minimum_nights"]).sum()), "lead_days_median": float(t["lead"].median()), "lead_days_max": int(t["lead"].max())} for s, t in q.groupby("stay")]
    pd.DataFrame(qrows).to_csv(R / "quote.csv", index=False)
    qj = q["price_quote_raw"].map(lambda s: json.loads(s)["quote"])                  # the quote is a JSON document inside the CSV
    disc = qj.map(lambda j: float(j["discount_amount"]) if j.get("discount_amount") is not None else np.nan); sub = qj.map(lambda j: float(j["discounted_subtotal"]) if j.get("discounted_subtotal") is not None else np.nan)
    tot = qj.map(lambda j: float(j["total_price"]) if j.get("total_price") is not None else np.nan); pn = pd.to_numeric(q["price_quote_price_per_night"], errors="coerce"); monthly = (q["stay"] == LONG); has = disc.notna(); both = disc.notna() & sub.notna(); share = (disc / (sub + disc))[monthly & both]
    qc = [("quotes read", len(q)), ("quotes with a cleaning fee", sum(j.get("cleaning_fee") is not None for j in qj)), ("quotes with a service fee", sum(j.get("service_fee") is not None for j in qj)), ("quotes with taxes", sum(j.get("taxes") is not None for j in qj)),
          ("quotes in US dollars", sum(j.get("currency") == "USD" for j in qj)), ("quotes with a discount", int(has.sum())), ("monthly-stay quotes with a discount", int((has & monthly).sum())), ("short-stay quotes with a discount", int((has & ~monthly).sum())),
          ("quotes with a total and a price per night", int((tot.notna() & pn.notna()).sum())), ("of which the total divided by the nights equals the price per night to the cent", int((np.abs(tot / q["nights"] - pn) <= 0.006)[tot.notna() & pn.notna()].sum())),
          ("quotes with both a total and a price after discount", int((tot.notna() & sub.notna()).sum())), ("of which the two are within a dollar", int(((tot - sub).abs() <= 1).sum())), ("monthly-stay quotes with a discount and a price after it", len(share)),
          ("their discount as a share of the price before it: median", float(share.median())), ("their discount as a share of the price before it: first quartile", float(share.quantile(0.25))), ("their discount as a share of the price before it: third quartile", float(share.quantile(0.75)))]
    pd.DataFrame(qc, columns=["item", "value"]).to_csv(R / "quote_contents.csv", index=False)
    add("detailed listings with a price quote", len(q)); add("quoted price per night equals the price (where both)", int((np.isclose(pd.to_numeric(q["price_quote_price_per_night"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").round(2), q["price_clean"], rtol=0, atol=0.011) | q["price_quote_price_per_night"].isna() | q["price_clean"].isna()).sum()))

    # Step 4: explore, on the full list (summary table): stay length, price, registration
    S["stay"] = np.where(S["minimum_nights"].isna(), "unknown", np.where(S["minimum_nights"] < 30, SHORT, LONG))
    stay = [{"stay_length": nm, "listings": int(((S["minimum_nights"] >= lo) & (S["minimum_nights"] <= hi)).sum())} for nm, lo, hi in STAY]
    st = pd.DataFrame(stay); st["share"] = st["listings"] / len(S); st.to_csv(R / "stay.csv", index=False)
    rows = []
    def put(kind, group, mask):
        for stay_name, sm in (("all", np.ones(len(S), bool)), (SHORT, (S["stay"] == SHORT).to_numpy()), (LONG, (S["stay"] == LONG).to_numpy())):
            t = S[mask & sm]; p = t["price"].dropna(); rows.append({"group_type": kind, "group": group, "stay": stay_name, "listings": len(t), "priced": len(p), **stats(p)})
    put("all", "All listings", np.ones(len(S), bool))
    for bname in BOROUGHS:
        put("borough", bname, (S["neighbourhood_group"] == bname).to_numpy())
    for rt in ("Entire home/apt", "Private room", "Hotel room", "Shared room"):
        put("room_type", rt, (S["room_type"] == rt).to_numpy())
    pd.DataFrame(rows).to_csv(R / "price.csv", index=False)
    cov = [{"availability_365": nm, "listings": int(mk.sum()), "priced": int(S.loc[mk, "price"].notna().sum())} for nm, mk in (("none (0 nights)", S["availability_365"] == 0), ("some (1 or more nights)", S["availability_365"] > 0))]
    c = pd.DataFrame(cov); c["share_priced"] = c["priced"] / c["listings"]; c.to_csv(R / "price_coverage.csv", index=False)
    S["reg"] = np.where(S["license"].isna(), "none", np.where(S["license"].astype(str).str.strip().str.upper() == "EXEMPT", "exempt", "number"))
    reg = [{"stay": s, "listings": int((S["stay"] == s).sum()), **{k: int(((S["stay"] == s) & (S["reg"] == k)).sum()) for k in ("number", "exempt", "none")}} for s in (SHORT, LONG)]
    pd.DataFrame(reg).to_csv(R / "registration.csv", index=False)
    pr = S["price"].dropna(); sm = {"listings": len(S), "short_stay": int((S["stay"] == SHORT).sum()), "monthly_stay": int((S["stay"] == LONG).sum()), "stay_unknown": int((S["stay"] == "unknown").sum()), "exactly_30": int((S["minimum_nights"] == 30).sum()),
          "private_rooms": int((S["room_type"] == "Private room").sum()), "entire_homes": int((S["room_type"] == "Entire home/apt").sum()), "priced": len(pr), "price_mean": float(pr.mean()), "price_median": float(pr.median()), "price_max": float(pr.max()),
          "priced_over_5000": int((pr > 5000).sum()), "priced_over_1000": int((pr > 1000).sum()), "price_p99": float(np.quantile(pr, 0.99))}
    pd.DataFrame(list(sm.items()), columns=["key", "value"]).to_csv(R / "summary.csv", index=False)
    pd.DataFrame(audit, columns=["check", "value"]).to_csv(R / "audit.csv", index=False)
    for f in ("audit", "agreement", "split_neighbourhoods", "quote", "quote_contents", "stay", "price", "price_coverage", "registration", "summary"):
        print("==", f); print(pd.read_csv(R / f"{f}.csv").round(3).to_string(index=False))


if __name__ == "__main__":
    main()

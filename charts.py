"""Step 6: charts.   ./venv/bin/python charts.py -> charts/00_cover.png, 01_stay_length.png, 02_map.png, 03_price.png, 04_registration.png, 05_reviews.png"""
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).parent
R, D = HERE / "results", HERE / "data"
INK, DIM, GRID, BG, BLUE, ORANGE, GRAY, GREEN = "#f2f2f0", "#8a8a87", "#1d1d1d", "#0b0b0b", "#3987e5", "#d95926", "#9a9a96", "#3aa876"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
                     "axes.edgecolor": "#3a3a3a", "axes.labelcolor": DIM, "xtick.color": DIM, "ytick.color": DIM,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 1,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 11, "axes.titlesize": 13,
                     "axes.titlelocation": "left", "axes.titlepad": 12})
SHORT, LONG, NONE = "under 30 nights", "30 nights or more", "#5a5a58"
L = pd.read_csv(D / "summary_listings.csv", usecols=["longitude", "latitude", "minimum_nights"]); G = json.load(open(D / "neighbourhoods.geojson"))
PRICE, STAY, REG, REV = (pd.read_csv(R / f"{f}.csv") for f in ("price", "stay", "registration", "reviews_by_year")); AUD = pd.read_csv(R / "audit.csv").set_index("check")["value"]
GROUPS = [("All listings", "All\nlistings"), ("Manhattan", "Manhattan"), ("Brooklyn", "Brooklyn"), ("Queens", "Queens"), ("Bronx", "Bronx"), ("Staten Island", "Staten\nIsland")]


def save(fig, name):
    fig.tight_layout(); fig.savefig(HERE / "charts" / name, dpi=150); plt.close(fig)


def outlines(ax):
    for f in G["features"]:
        g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for part in parts:
            for ring in part:
                xs, ys = zip(*ring); ax.plot(xs, ys, color="#2e2e2e", linewidth=0.5, solid_joinstyle="round")
    ax.set_xlim(-74.27, -73.69); ax.set_ylim(40.48, 40.93); ax.set_aspect(1 / np.cos(np.radians(40.7))); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def dots(ax, short, monthly):
    if monthly:
        m = L[L["minimum_nights"] >= 30]; ax.scatter(m["longitude"], m["latitude"], s=1.4, color=BLUE, alpha=0.3, linewidths=0)
    if short:
        m = L[L["minimum_nights"] < 30]; ax.scatter(m["longitude"], m["latitude"], s=2.6, color=ORANGE, alpha=0.65, linewidths=0)


def stay_length(ax):
    x = np.arange(len(STAY)); v = 100 * STAY["share"]
    ax.bar(x, v, color=[ORANGE] * 4 + [BLUE] * 2, width=0.62)
    for xi, vi in zip(x, v):
        ax.text(xi, vi + 1.5, f"{vi:.1f}%", ha="center", fontsize=10, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([f"{n}\n{c:,}" for n, c in zip(STAY["stay_length"], STAY["listings"])]); ax.set_ylabel("% of listings"); ax.set_ylim(0, 92); ax.grid(axis="x", visible=False)
    ax.text(3.55, 58, "30 nights is where the city's\nregistration rule stops applying", ha="right", va="center", fontsize=9.5, color=INK)
    ax.legend(handles=[Patch(color=ORANGE, label=SHORT), Patch(color=BLUE, label=LONG)], frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    ax.set_title(f"Minimum stay set by the host: share of the {int(AUD['rows: summary listings']):,} listings (count below each bar)")


def price_bars(ax, size=9):
    x = np.arange(len(GROUPS)); w = 0.38
    for dx, stay, col, lab in ((-w / 2, SHORT, ORANGE, "under 30 nights"), (w / 2, LONG, BLUE, "30 nights or more")):
        t = [PRICE[(PRICE["group"] == g) & (PRICE["stay"] == stay)].iloc[0] for g, _ in GROUPS]; ax.bar(x + dx, [r["median"] for r in t], width=w * 0.92, color=col, label=lab)
        for xi, r in zip(x + dx, t):
            ax.vlines(xi, r["q1"], r["q3"], color=INK, alpha=0.6, linewidth=1.3); ax.text(xi, r["q3"] + 14, f"${r['median']:,.0f}", ha="center", fontsize=size, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([n for _, n in GROUPS]); ax.set_ylim(0, 710); ax.set_ylabel("median price a night (USD)"); ax.grid(axis="x", visible=False)
    ax.legend(handles=[Patch(color=ORANGE, label="under 30 nights"), Patch(color=BLUE, label="30 nights or more"), Line2D([0], [0], color=INK, alpha=0.6, linewidth=1.3, label="middle half of listings")], frameon=False, labelcolor=INK, fontsize=9, loc="upper right")


def registration(ax):
    cols = {"number": GREEN, "exempt": GRAY, "none": NONE}; names = {"number": "a registration number", "exempt": "Exempt", "none": "nothing"}
    for yi, (_, r) in zip((1, 0), REG.iterrows()):
        left = 0
        for k in ("number", "exempt", "none"):
            w = 100 * r[k] / r["listings"]; ax.barh(yi, w, left=left, color=cols[k], height=0.56)
            if w >= 7:
                ax.text(left + w / 2, yi, f"{int(r[k]):,}\n{w:.1f}%", ha="center", va="center", fontsize=9.5, color=BG if k != "none" else INK)
            left += w
        if r["stay"] == LONG:
            ax.text(100.8, yi, f"{int(r['number'])} with a number,\n{int(r['exempt'])} Exempt", va="center", fontsize=8.5, color=DIM)
    ax.set_yticks([1, 0]); ax.set_yticklabels([f"{r['stay'].capitalize()}\n{int(r['listings']):,} listings" for _, r in REG.iterrows()]); ax.set_xlim(0, 122); ax.set_xticks([0, 20, 40, 60, 80, 100]); ax.set_xlabel("% of listings"); ax.grid(axis="y", visible=False)
    ax.legend(handles=[Patch(color=cols[k], label=f"shows {names[k]}" if k != "exempt" else "shows Exempt") for k in cols], frameon=False, labelcolor=INK, fontsize=9, loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=3)
    ax.set_title("What the registration field says, by minimum stay")


def date_text(v):
    return datetime.strptime(str(int(v)), "%Y%m%d").strftime("%-d %B %Y")


def reviews(ax):
    ax.bar(REV["year"], REV["reviews"] / 1000, color=BLUE, width=0.72); ax.patches[-1].set_alpha(0.55)
    ax.set_xticks(REV["year"]); ax.set_xticklabels([str(y) if i % 2 == 0 else "" for i, y in enumerate(REV["year"])], fontsize=9); ax.set_ylabel("reviews written (thousands)"); ax.grid(axis="x", visible=False); ax.set_ylim(0, REV["reviews"].max() / 1000 * 1.2)
    ax.text(REV["year"].iloc[0] - 0.4, 12, f"first review\n{date_text(AUD['reviews: earliest date'])}", fontsize=9, color=INK, va="bottom")
    ax.text(REV["year"].iloc[-1] + 0.4, REV["reviews"].max() / 1000 + 8, f"last review {date_text(AUD['reviews: latest date'])}\n(2026 is a part year)", fontsize=9, color=INK, ha="right", va="bottom")
    ax.set_title(f"Reviews of today's listings, by the year they were written ({int(AUD['rows: reviews']):,} in all)")


def main():
    (HERE / "charts").mkdir(exist_ok=True)
    med = lambda stay: PRICE[(PRICE["group"] == "All listings") & (PRICE["stay"] == stay)].iloc[0]["median"]
    fig = plt.figure(figsize=(14, 8)); g = fig.add_gridspec(1, 2, width_ratios=[1, 1.15]); a = fig.add_subplot(g[0]); b = fig.add_subplot(g[1])
    outlines(a); dots(a, True, True); a.set_title("Each dot is a listing", fontsize=14); a.legend(handles=[Patch(color=ORANGE, label=f"under 30 nights ({int((L['minimum_nights'] < 30).sum()):,})"), Patch(color=BLUE, label=f"30 nights or more ({int((L['minimum_nights'] >= 30).sum()):,})")], frameon=False, labelcolor=INK, fontsize=10, loc="lower right")
    price_bars(b, 10); b.set_title("Median price a night, by borough and minimum stay", fontsize=14)
    fig.suptitle(f"What does a night in New York cost on Airbnb? \\${med(SHORT):,.0f} for a short stay, \\${med(LONG):,.0f} on a monthly one", x=0.01, ha="left", fontsize=20, color=INK, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(HERE / "charts" / "00_cover.png", dpi=100); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3.8)); stay_length(ax); save(fig, "01_stay_length.png")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, (short, monthly, ttl, col) in zip(axes, ((False, True, "30 nights or more", BLUE), (True, False, "Under 30 nights", ORANGE))):
        outlines(ax); dots(ax, short, monthly); n = int((L["minimum_nights"] >= 30).sum()) if monthly else int((L["minimum_nights"] < 30).sum()); ax.set_title(f"{ttl}: {n:,} listings", fontsize=12)
    save(fig, "02_map.png")
    fig, ax = plt.subplots(figsize=(10, 3.8)); price_bars(ax); ax.set_title("Median price a night, by borough and minimum stay"); save(fig, "03_price.png")
    fig, ax = plt.subplots(figsize=(10, 3.4)); registration(ax); save(fig, "04_registration.png")
    fig, ax = plt.subplots(figsize=(10, 3.6)); reviews(ax); save(fig, "05_reviews.png")


if __name__ == "__main__":
    main()

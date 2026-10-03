"""Step 1: the Inside Airbnb New York City files of 14 June 2026: five files in four formats.

    ./venv/bin/python download.py   -> data/ (5 files), results/pull.json

Inside Airbnb (insideairbnb.com/get-the-data), "New York City, 14 June 2026", licensed under Creative Commons Attribution 4.0. Public listing information collected from airbnb.com. The files are:
listings.csv.gz (the detailed listings, gzipped CSV), summary_listings.csv (the short listings table, plain CSV), neighbourhoods.csv, neighbourhoods.geojson (the neighbourhood outlines, JSON)
and reviews.csv (listing id and date of every review, plain CSV). About 45 MB, so none of it is committed; this script fetches it. Host names, listing titles and descriptions are in the files
and are never used or published here: the results are counts and summaries.
"""
import csv
import gzip
import hashlib
import io
import json
import ssl
import urllib.request
from datetime import date
from pathlib import Path

import certifi

HERE = Path(__file__).parent
BASE = "https://data.insideairbnb.com/united-states/ny/new-york-city/2026-06-14/"
FILES = {"listings.csv.gz": "data/listings.csv.gz", "summary_listings.csv": "visualisations/listings.csv", "neighbourhoods.csv": "visualisations/neighbourhoods.csv",
         "neighbourhoods.geojson": "visualisations/neighbourhoods.geojson", "reviews.csv": "visualisations/reviews.csv"}
CTX = ssl.create_default_context(cafile=certifi.where())


def main():
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "results").mkdir(exist_ok=True)
    info = {"pulled": date.today().isoformat(), "files": {}}
    for name, path in FILES.items():
        blob = urllib.request.urlopen(urllib.request.Request(BASE + path, headers={"User-Agent": "research-portfolio (Rishit Raj Mathur)"}), context=CTX, timeout=300).read()
        (HERE / "data" / name).write_bytes(blob)
        text = gzip.decompress(blob).decode("utf-8") if name.endswith(".gz") else blob.decode("utf-8")
        rows = len(list(csv.reader(io.StringIO(text)))) - 1 if name.endswith((".csv", ".csv.gz")) else len(json.loads(text)["features"])
        info["files"][name] = {"url": BASE + path, "bytes": len(blob), "rows": rows, "sha256": hashlib.sha256(blob).hexdigest()}
    (HERE / "results" / "pull.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: (v["rows"], v["bytes"]) for k, v in info["files"].items()}, indent=1))


if __name__ == "__main__":
    main()

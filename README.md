# What does a night in New York cost on Airbnb?

The New York City listings that Inside Airbnb collected from airbnb.com in June 2026: five files in three formats, imported, cleaned, combined and then questioned. Five questions:
- do the files agree once they are combined (the two listings tables, the reviews and the neighbourhood outlines);
- how long are the minimum stays, and so how many listings can be booked for a night;
- what does "a night" mean in the price column, and what does one cost, by borough and room type;
- which listings show a registration number, and how does that line up with the minimum stay;
- the three questions of the course task: the earliest and latest review dates, how many listings are private rooms, and the average price.

The questions follow DataCamp's "Exploring the NYC Airbnb Market" (import, clean and combine listings from several file types), answered on the real current files instead of its course files.

Build log: https://mrrishit909.github.io/projects/nyc-airbnb-cleaning/

## Data

Inside Airbnb (https://insideairbnb.com/get-the-data/), New York City, 14 June 2026; the listings were collected on 4 dates from 14 to 23 June 2026. Licensed under Creative Commons Attribution 4.0; attribution: Inside Airbnb (insideairbnb.com). Public listing information from airbnb.com.
The five files are `listings.csv.gz` (the detailed listings: 30,259 rows, 90 columns), `summary_listings.csv` (30,555 rows, 19 columns), `neighbourhoods.csv` (230 names), `neighbourhoods.geojson` (233 outlines) and `reviews.csv` (990,170 rows: a listing and a date).
About 44 MB, so none is committed; `results/pull.json` has the URLs, row counts and checksums. Host names, listing titles and descriptions are in the files and are never used or published: the results are counts and summaries. Inside Airbnb says Airbnb anonymises each listing's location to within 150 metres of the real address.

```
./venv/bin/pip install pandas numpy matplotlib certifi      # in a venv
./venv/bin/python download.py    # data/*
./venv/bin/python analyze.py     # results/*
./venv/bin/python check.py
./venv/bin/python charts.py
```

## Steps

1. **Download** the five files, with their checksums.
2. **Audit and clean.** The price is text ("$1,234.56") and becomes a number; the registration field is trimmed and put in upper case; dates are parsed; the price quote, a JSON document inside a CSV column, is read. Each conversion is counted, and none fails.
3. **Combine.** The two listings tables are compared field by field on the ids they share. The summary table holds every listing in the detailed one plus 296 more, so it is the full list: 30,555 listings, with the price in whole dollars (checked against the cleaned detailed price). The reviews are checked against each listing's review count and dates, and each listing's coordinates against the outline of its own neighbourhood.
4. **Explore** the full list: minimum stay, what the price quote priced, the price by borough and room type (the median and the middle half, with the mean for the course question), how many listings have a price, and the registration field by minimum stay.
5. **Check.** `check.py` recounts everything in plain Python (the csv, gzip, json and re modules and loops: no pandas, numpy or matplotlib), including a ray-casting point-in-polygon test of every listing against its own outline: 380 numbers. Changing the stay threshold, the quantile rule, the half-up rounding, the registration classes or the polygon test makes it fail.
6. **Charts.**

## Results

- **The files agree, with two holes.** All 14 fields compared between the two listings tables (room type, minimum stay, review count and date, registration, neighbourhood, host, coordinates, availability and more) are identical for all 30,259 listings in both, and the summary price is the detailed price rounded half up to the dollar for all 21,515 that are priced (the largest gap is 50 cents).
  The first hole: the summary table has 296 listings the detailed one lacks. All are private rooms with a minimum stay under 30 nights; none has a registration field; 246 are in Manhattan and 282 have a price. The second: the reviews file covers 21,939 listings, every one in the summary table; the 239 that are missing from the detailed table are among those 296.
  Each listing's review count equals its rows in the reviews file for all 30,555, its last review date equals its latest review (or both are blank), and so does its first review date in the detailed table. Every listing is inside the outline of its own neighbourhood; the 233 outlines are for 230 neighbourhoods (Bayswater, City Island and Howard Beach are each drawn in two pieces), and 7 neighbourhoods have no listing.
- **A night is not a night.** The minimum stay is 30 nights or more for 24,717 listings (80.9%) and exactly 30 for 23,802 (77.9%); only 5,836 (19.1%) can be booked for fewer, 4,143 of them for a single night. Thirty nights is also where the city's registration rule stops applying: stays of 30 consecutive days or more are exempt (https://www.nyc.gov/site/specialenforcement/registration-law/registration.page).
- **What the price is.** The price column is not a list price. Airbnb was asked for a quote for one particular stay, and the price is that quote's total, after any discount, divided by its nights (for all 21,514 quotes that have both a total and a price per night, the total divided by the nights equals the price to the cent). For the 17,582 monthly-stay listings with a quote the stay was 30 nights for nearly all (17,483 quotes equal the listing's minimum stay) and began a median 36 days after the scrape (up to 335);
  8,741 of them (49.7%) carry a discount, a median 17.6% off the price before it (middle half 9.0% to 20.5%). For the 5,096 short-stay listings with a quote the median stay was 1 night, starting a median 4 days after the scrape. None of the 22,678 quotes includes a cleaning fee or a service fee, and only 58 include taxes: the price is the accommodation charge, not what a guest pays at checkout.
- **What a night costs.** 21,797 of the 30,555 listings (71.3%) have a price. Their median is $176 a night and their mean $278.33: the mean is pulled up by 622 listings over $1,000 and 38 over $5,000 (the highest is $30,973), so the median is the better typical price. By minimum stay the median is $303 for short stays (middle half $203 to $485) and $143 for monthly ones ($81 to $240).
  In every borough short stays cost more: Manhattan $381 against $199, Brooklyn $268 against $127, Queens $209 against $98, the Bronx $167 against $97 and Staten Island $200 against $97 (only 142 and 53 short stays are priced in the last two). The gap holds in every room type: entire homes $404.50 against $202, private rooms $248 against $77; hotel rooms and shared rooms are in `results/price.csv`.
- **The course questions.** The reviews run from 25 May 2009 to 22 June 2026. 13,009 of the 30,555 listings (42.6%) are private rooms and 16,808 (55.0%) entire homes. The average price is $278.33 (the median $176, as above).
- **Missing prices.** 8,758 listings (28.7%) have no price. Most of them (6,800, or 77.6%) have no availability in the next 365 days: 6,800 of the 6,801 listings with no availability have no price, against 8.2% of the 23,754 that have some. Short stays are priced more often than monthly ones (90.8% against 66.7%), so the prices describe the listings that can be booked.
- **Registration.** Of the 5,836 short-stay listings, 2,268 (38.9%) show a registration number, 2,905 (49.8%) say Exempt and 663 (11.4%) show nothing. Of the 24,717 monthly-stay listings, 24,605 (99.5%) show nothing, 61 a number and 51 Exempt.
  The 2,330 registration numbers in the detailed table are 2,013 distinct numbers: 255 numbers appear on more than one listing (572 listings, up to 6 on one number); the data does not say why. 23 numbers differed only in case or spaces and were cleaned.
- **Reviews over time.** 990,170 reviews of 21,939 listings; 8,616 listings have none. Per year they rise from 41 in 2009 to 91,559 in 2019, fall to 36,683 in 2020 and reach 148,331 in 2023 (58,572 so far in 2026). The file holds only reviews of listings still on Airbnb in June 2026, so the early years are understated.

## Not done, and caveats

- The price is a quote for one stay, not what guests paid and not an average over the year: the monthly-stay quotes were made for check-in dates up to 335 days after the scrape, in different seasons. It has no cleaning or service fee. Short and monthly prices are not like for like: they price different stay lengths (a median of 1 night against 30, with a discount on about half of the monthly quotes), and they are different listings, even though the gap holds within room types.
- The medians describe the 71.3% of listings that have a price, mostly those with availability in the next year; listings that are fully blocked are missing.
- The registration field shows what a listing says, not whether it is legal or compliant. "Exempt" is the field's own word: the city exempts stays of 30 consecutive days or more and units in Class B multiple dwellings, and the data does not say which applies. The 663 short-stay listings that show nothing include all 296 that have no detailed record; the data does not say why.
- A listing is not a unit or a host: the same apartment or host can appear more than once, and hosts were not analysed.
- Coordinates are anonymised by Airbnb to within 150 metres, and every listing falls inside its own neighbourhood outline: that is a consistency check, which shows the files were made together, not proof that a location is exact.
- A snapshot of one month (14 to 23 June 2026): no trend or season. The calendar file (availability and price by day), review text and host details were not downloaded or used.
- Free to use with attribution (CC BY 4.0). Inside Airbnb itself says the accuracy of the information compiled from the Airbnb site is not its responsibility; this is a portfolio project.

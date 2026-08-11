# Indian State Election Exit Poll Accuracy Analysis

There are a lot of pollsters in India that present their projections of elections. I wanted to have a metric to understand whom to believe, and to create a record that holds them accountable. I might eventually do this for opinion polls, but for now these are exit polls only.

This was viberesearched and vibecoded with Claude Code Opus 4.5. I used it both for research/scraping and for processing. All errors are either Claude's or mine.

See ```exitpoll_accuracy.csv``` for raw data, transcribed primarily from Wikipedia and supplemented with additional exit polls found via news archives and Wayback Machine snapshots (see `source` column for the citation on each row).

## Notes
I had to manually do some harmonizing, so there may be errors. Not all pollsters' forecasts may have been logged on Wikipedia, so they would not show up here — I've since gone back and added a batch of pollsters that Wikipedia missed or later trimmed, each backed by a reputable news source or an archived Wikipedia revision (see the `source` column).

If there are any errors, let me know.

## What are exit polls? Exit polls are surveys conducted immediately after voters leave polling stations on election day. They are published after voting ends but before official results are announced. This dataset measures how accurately these exit polling agencies predicted the actual election outcomes.

**Dataset**: 329 exit polls across 35 state legislative assembly elections (2020-2026)

## Best Pollsters by Interval Score (min 5 polls)

| Rank | Pollster | Polls | Avg intervalscore |
|------|----------|-------|-------------------|
| 1 | Today's Chanakya | 21 | 0.241 |
| 2 | Axis My India | 34 | 0.253 |
| 3 | Jan Ki Baat | 21 | 0.293 |
| 4 | CNX | 17 | 0.298 |
| 5 | Zee-DesignBoxed | 5 | 0.315 |
| 6 | CVoter | 24 | 0.327 |
| 7 | P-Marq | 27 | 0.347 |
| 8 | Polstrat | 14 | 0.351 |
| 9 | People's Insight | 13 | 0.382 |
| 10 | Matrize | 21 | 0.421 |

Lower is better. The Winkler interval score penalizes both wide ranges and predictions that miss the actual result. This is my preferred metric.

## Best Pollsters by Abserror (min 5 polls)

| Rank | Pollster | Polls | Avg abserror |
|------|----------|-------|--------------|
| 1 | Today's Chanakya | 21 | 0.0655 |
| 2 | Axis My India | 34 | 0.0676 |
| 3 | CNX | 17 | 0.0780 |
| 4 | Jan Ki Baat | 21 | 0.0798 |
| 5 | CVoter | 24 | 0.0880 |
| 6 | Sudarshan News | 5 | 0.0897 |
| 7 | Polstrat | 14 | 0.0911 |
| 8 | Zee-DesignBoxed | 5 | 0.0914 |
| 9 | P-Marq | 27 | 0.0943 |
| 10 | People's Insight | 13 | 0.0993 |

Lower is better. Measures average distance to correct number of seats |midpoint - actual| / total_seats across parties.

## Best Pollsters by Winner Prediction (min 5 polls)

| Rank | Pollster | Polls | Winner Correct |
|------|----------|-------|----------------|
| 1 | People's Insight | 13 | 84.6% |
| 2 | Axis My India | 34 | 82.4% |
| 3 | Today's Chanakya | 21 | 81.0% |
| 4 | Sudarshan News | 5 | 80.0% |
| 5 | Zeenia | 5 | 80.0% |
| 6 | Polstrat | 14 | 78.6% |
| 7 | JVC | 9 | 77.8% |
| 8 | P-Marq | 27 | 77.8% |
| 9 | CNX | 17 | 76.5% |
| 10 | Chanakya Strategies | 8 | 75.0% |

Winner prediction = correctly predicting the party/alliance that would win the most seats.

---

## Methodology

### Data Collection

Exit poll predictions were manually transcribed, primarily from Wikipedia pages for each state election, and supplemented with additional pollsters found via news archives and archived (Wayback Machine) Wikipedia revisions when the live Wikipedia table had missed or since dropped a pollster. Done manually by Claude! Each row contains:
- The pollster name (e.g., "India Today-Axis My India")
- Seat predictions as ranges `[min, max]` for each party
- Actual election results
- A `source` citation — either the Wikipedia page it was transcribed from, or the specific news article / archived revision it was found in

Every added row is required to have a citable, reputable, dated-before-results source (an established news outlet, Wikipedia, or a recognized pollster's own release) — single-sourced claims from unknown one-off "pollsters," tweets, or self-published pages are excluded, since a number of fabricated or low-credibility "exit polls" circulate online.

"Poll of Polls" (a recurring name in Wikipedia's exit-poll tables, most likely NDTV's own aggregate feature) is deliberately excluded — its predictions are always point values, not ranges, and checking them against the other listed pollsters for the same election shows they're essentially the average of those other pollsters' midpoints. It isn't an independent survey, so it doesn't belong in a "which pollster is most accurate" comparison — averaging structurally reduces error regardless of skill, which would make it look artificially strong. Don't re-add it if it turns up again in future transcription.

### Processing

Run `python3 process_polls.py` to generate scores. The script:

1. **Harmonizes pollster names** - Maps variants like "India Today-Axis My India", "Aaj Tak-Axis My India" to canonical "Axis My India"

2. **Expands single-value predictions** - If a pollster gives only point estimates (no ranges), expands them using the average range width from other pollsters in that election

3. **Calculates accuracy metrics** for each poll

### Accuracy Metrics

**Interval Score (Winkler)**: For each scored party:
- If actual is in predicted range: `score = width`
- If actual is outside range: `score = width + (2/α) × distance`

A party is scored if it actually won ≥1 seat (whether the poll predicted it or omitted it entirely — an omission is scored as a `[0,0]` forecast), **or** if the poll predicted a nonzero floor for it (i.e. confidently called it a seat-winner) and it ended up with zero seats. A poll that hedges with a floor of 0 for a party that does end up with 0 seats isn't scored on that party at all — it's neither a real prediction nor a real miss, and including it would just dilute the score with easy, uninformative "correct" calls.

This is a 'proper scoring rule', assuming pollsters aim to publish (1-α) confidence intervals. In the scoring above I used α=0.5. So pollsters are assumed to be targeting 50% coverage - i.e., they expect to be within range half the time. (In practice, they're within range only 31% of the time.)

Aggregated as `(1 / (total_seats × num_parties)) × sum(scores)`. Lower is better - penalizes both wide ranges and misses. `num_parties` is the count of parties scored above — dividing by `total_seats × num_parties` is what makes the score comparable across elections of very different sizes (e.g. Mizoram's 40 seats vs. West Bengal's 294): a 90-seat election scored across 3 parties divides by 270, a 294-seat election scored across 4 divides by 1176.

**Abserror**: Average of `|midpoint - actual| / total_seats` across every predicted party plus any actual winner the poll omitted (a broader set than intervalscore's — it doesn't exclude hedged-and-correct zero calls). A value of 0.06 means predictions are off by 6% of total seats on average. If an actual seat-winning category is omitted from a poll, it is scored as a zero-seat forecast.

**Winner Correct**: Did the poll correctly predict which party would win the most seats? If a poll ties for the highest midpoint, it is counted correct when the actual winner is one of the tied top parties. Unlike the other two metrics, this isn't normalized at all — it's a raw 0/1 per poll, only averaged when aggregating across polls for the rankings above.

### Elections Covered

| Year | Elections |
|------|-----------|
| 2026 | Assam, Kerala, Tamil Nadu, Puducherry, West Bengal |
| 2025 | Bihar, Delhi |
| 2024 | Maharashtra, Jharkhand, Haryana, J&K, Andhra Pradesh, Odisha |
| 2023 | Karnataka, Chhattisgarh, Rajasthan, MP, Telangana, Mizoram, Meghalaya, Tripura, Nagaland |
| 2022 | Gujarat, Himachal Pradesh, Punjab, UP, Goa, Uttarakhand, Manipur |
| 2021 | West Bengal, Assam, Tamil Nadu, Kerala |
| 2020 | Bihar, Delhi |

### Corrections

Rajasthan 2023's P-Marq row originally showed INC+ as [69, 91], transcribed from Wikipedia. Republic World's own primary article (the pollster's original publisher) states INC+ [69, 81]; corrected to match the primary source, noted in that row's `source` column.

### Files

| File | Description |
|------|-------------|
| `exitpoll_accuracy.csv` | Raw transcribed data (source of truth) |
| `exitpoll_accuracy_harmonized.csv` | Processed output with scores |
| `process_polls.py` | Processing script |

---

*Data sources: Wikipedia exit poll tables plus additional reputable news sources for Indian state legislative assembly elections — see the `source` column in `exitpoll_accuracy.csv` for the citation on each row.*

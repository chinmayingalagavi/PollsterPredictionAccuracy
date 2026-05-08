# Indian State Election Exit Poll Accuracy Analysis

There are a lot of pollsters in India that present their projections of elections. I wanted to have a metric to understand whom to believe, and to create a record that holds them accountable. I might eventually do this for opinion polls, but for now these are exit polls only.

This was viberesearched and vibecoded with Claude Code Opus 4.5. I used it both for research/scraping and for processing. All errors are either Claude's or mine.

See ```exitpoll_accuracy.csv``` for raw data scraped from Wikipedia.

## Notes
I had to manually do some harmonizing, so there may be errors. Not all pollsters' forecasts may have been logged on Wikipedia, so they would not show up here.

If there are any errors, let me know.

## What are exit polls? Exit polls are surveys conducted immediately after voters leave polling stations on election day. They are published after voting ends but before official results are announced. This dataset measures how accurately these exit polling agencies predicted the actual election outcomes.

**Dataset**: 288 exit polls across 35 state legislative assembly elections (2020-2026)

## Best Pollsters by Interval Score (min 4 polls)

| Rank | Pollster | Polls | Avg intervalscore |
|------|----------|-------|-------------------|
| 1 | Today's Chanakya | 21 | 0.240 |
| 2 | Poll of Polls | 12 | 0.245 |
| 3 | Axis My India | 33 | 0.246 |
| 4 | Zee-DesignBoxed | 4 | 0.260 |
| 5 | CNX | 14 | 0.274 |
| 6 | Veto | 4 | 0.281 |
| 7 | CVoter | 23 | 0.301 |
| 8 | Jan Ki Baat | 18 | 0.309 |
| 9 | Polstrat | 12 | 0.341 |
| 10 | P-Marq | 23 | 0.355 |

Lower is better. The Winkler interval score penalizes both wide ranges and predictions that miss the actual result. This is my preferred metric.

## Best Pollsters by Abserror (min 4 polls)

| Rank | Pollster | Polls | Avg abserror |
|------|----------|-------|--------------|
| 1 | Axis My India | 33 | 0.0640 |
| 2 | Today's Chanakya | 21 | 0.0654 |
| 3 | Poll of Polls | 12 | 0.0696 |
| 4 | CNX | 14 | 0.0729 |
| 5 | Veto | 4 | 0.0752 |
| 6 | Zee-DesignBoxed | 4 | 0.0776 |
| 7 | CVoter | 23 | 0.0811 |
| 8 | Jan Ki Baat | 18 | 0.0811 |
| 9 | Polstrat | 12 | 0.0880 |
| 10 | P-Marq | 23 | 0.0896 |

Lower is better. Measures average distance to correct number of seats |midpoint - actual| / total_seats across parties.

## Best Pollsters by Winner Prediction (min 4 polls)

| Rank | Pollster | Polls | Winner Correct |
|------|----------|-------|----------------|
| 1 | Axis My India | 33 | 84.8% |
| 2 | People's Insight | 12 | 83.3% |
| 3 | Poll of Polls | 12 | 83.3% |
| 4 | P-Marq | 23 | 82.6% |
| 5 | Today's Chanakya | 21 | 81.0% |
| 6 | CNX | 14 | 78.6% |
| 7 | JVC | 9 | 77.8% |
| 8 | Polstrat | 12 | 75.0% |
| 9 | Veto | 4 | 75.0% |
| 10 | Zee-DesignBoxed | 4 | 75.0% |

Winner prediction = correctly predicting the party/alliance that would win the most seats.

---

## Methodology

### Data Collection

Exit poll predictions were manually transcribed from Wikipedia pages for each state election. Done manually by Claude! Each row contains:
- The pollster name (e.g., "India Today-Axis My India")
- Seat predictions as ranges `[min, max]` for each party
- Actual election results

### Processing

Run `python3 process_polls.py` to generate scores. The script:

1. **Harmonizes pollster names** - Maps variants like "India Today-Axis My India", "Aaj Tak-Axis My India" to canonical "Axis My India"

2. **Expands single-value predictions** - If a pollster gives only point estimates (no ranges), expands them using the average range width from other pollsters in that election

3. **Calculates accuracy metrics** for each poll

### Accuracy Metrics

**Interval Score (Winkler)**: For each party that won ≥1 seat:
- If actual is in predicted range: `score = width`
- If actual is outside range: `score = width + (2/α) × distance`

This is a 'proper scoring rule', assuming pollsters aim to publish (1-α) confidence intervals. In the scoring above I used α=0.5. So pollsters are assumed to be targeting 50% coverage - i.e., they expect to be within range half the time. (In practice, they're within range only 31% of the time.)

Aggregated as `(1 / (total_seats × num_parties)) × sum(scores)`. Lower is better - penalizes both wide ranges and misses.

**Abserror**: Average of `|midpoint - actual| / total_seats` across scored parties. A value of 0.06 means predictions are off by 6% of total seats on average. If an actual seat-winning category is omitted from a poll, it is scored as a zero-seat forecast.

**Winner Correct**: Did the poll correctly predict which party would win the most seats? If a poll ties for the highest midpoint, it is counted correct when the actual winner is one of the tied top parties.

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

Note: West Bengal 2026 is provisional. The Falta seat was still pending when this dataset was updated, so the current file assumes Falta goes to AITC+ and records the actual result as BJP 207, AITC+ 81, Others 6. This may need to be changed after the official Falta result is announced.

### Files

| File | Description |
|------|-------------|
| `exitpoll_accuracy.csv` | Raw transcribed data (source of truth) |
| `exitpoll_accuracy_harmonized.csv` | Processed output with scores |
| `process_polls.py` | Processing script |

---

*Data source: Wikipedia exit poll tables for Indian state legislative assembly elections.*

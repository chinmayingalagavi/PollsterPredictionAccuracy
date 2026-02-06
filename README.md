# Indian State Election Exit Poll Accuracy Analysis

There are a lot of pollsters in India that present their projections of elections. I wanted to have a metric to understand whom to believe, and to create a record that holds them accountable. I might eventually do this for opinion polls, but for now these are exit polls only.

This was viberesearched and vibecoded with Claude Code Opus 4.5. I used it both for research/scraping and for processing. All errors are either Claude's or mine.

See ```exitpoll_accuracy.csv``` for raw data scraped from Wikipedia.

**What are exit polls?** Exit polls are surveys conducted immediately after voters leave polling stations on election day. They are published after voting ends but before official results are announced. This dataset measures how accurately these exit polling agencies predicted the actual election outcomes.

**Dataset**: 230 exit polls across 29 state legislative assembly elections (2020-2025)

## Best Pollsters by Interval Score (min 5 polls)

| Rank | Pollster | Polls | Avg intervalscore |
|------|----------|-------|-------------------|
| 1 | Today's Chanakya | 17 | 0.233 |
| 2 | Axis My India | 28 | 0.236 |
| 3 | Poll of Polls | 12 | 0.244 |
| 4 | CNX | 14 | 0.274 |
| 5 | People's Insight | 8 | 0.286 |
| 6 | CVoter | 22 | 0.306 |
| 7 | P-Marq | 18 | 0.308 |
| 8 | Jan Ki Baat | 18 | 0.310 |
| 9 | Polstrat | 12 | 0.341 |
| 10 | Matrize | 16 | 0.386 |

Lower is better. The Winkler interval score penalizes both wide ranges and predictions that miss the actual result. This is my preferred metric.

## Best Pollsters by Abserror (min 5 polls)

| Rank | Pollster | Polls | Avg abserror |
|------|----------|-------|--------------|
| 1 | Axis My India | 28 | 0.0631 |
| 2 | Today's Chanakya | 17 | 0.0649 |
| 3 | Poll of Polls | 12 | 0.0693 |
| 4 | CNX | 14 | 0.0731 |
| 5 | People's Insight | 8 | 0.0798 |
| 6 | P-Marq | 18 | 0.0812 |
| 7 | CVoter | 22 | 0.0815 |
| 8 | Jan Ki Baat | 18 | 0.0815 |
| 9 | Polstrat | 12 | 0.0880 |
| 10 | Matrize | 16 | 0.0993 |

Lower is better. Measures average distance to correct number of seats |midpoint - actual| / total_seats across parties.

## Best Pollsters by Winner Prediction (min 5 polls)

| Rank | Pollster | Polls | Winner Correct |
|------|----------|-------|----------------|
| 1 | People's Insight | 8 | 87.5% |
| 2 | P-Marq | 18 | 83.3% |
| 3 | Poll of Polls | 12 | 83.3% |
| 4 | Axis My India | 28 | 82.1% |
| 5 | CNX | 14 | 78.6% |
| 6 | Today's Chanakya | 17 | 76.5% |
| 7 | Polstrat | 12 | 75.0% |
| 8 | Matrize | 16 | 68.8% |
| 9 | Jan Ki Baat | 18 | 66.7% |
| 10 | CVoter | 22 | 63.6% |

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

This is a 'proper scoring rule', assuming pollsters aim to publish (1-α) confidence intervals. In the scoring above I used α=0.5. So pollsters are assumed to be targeting 50% coverage - i.e., they expect to be within range half the time. (In practice, they're within range only 38% of the time.)

Aggregated as `(1 / (total_seats × num_parties)) × sum(scores)`. Lower is better - penalizes both wide ranges and misses.

**Abserror**: Average of `|midpoint - actual| / total_seats` across parties. A value of 0.06 means predictions are off by 6% of total seats on average.

**Winner Correct**: Did the poll correctly predict which party would win the most seats?

### Elections Covered

| Year | Elections |
|------|-----------|
| 2025 | Delhi |
| 2024 | Maharashtra, Jharkhand, Haryana, J&K, Andhra Pradesh, Odisha |
| 2023 | Karnataka, Chhattisgarh, Rajasthan, MP, Telangana, Mizoram, Meghalaya, Tripura, Nagaland |
| 2022 | Gujarat, Himachal Pradesh, Punjab, UP, Goa, Uttarakhand, Manipur |
| 2021 | West Bengal, Assam, Tamil Nadu, Kerala |
| 2020 | Bihar, Delhi |

### Files

| File | Description |
|------|-------------|
| `exitpoll_accuracy.csv` | Raw transcribed data (source of truth) |
| `exitpoll_accuracy_harmonized.csv` | Processed output with scores |
| `process_polls.py` | Processing script |

---

*Data source: Wikipedia exit poll tables for Indian state legislative assembly elections.*

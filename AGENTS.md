# Indian State Election Exit Poll Accuracy Dataset

This project tracks the accuracy of **exit polls** for Indian state legislative assembly elections. Exit polls are surveys conducted immediately after voters leave polling stations, published before official results are announced (typically 1-3 days before counting).

## Project Goal

Measure how accurately Indian exit polls predict election outcomes, identify which pollsters are most reliable, and understand when/why exit polls fail.

## Files

| File | Description | Editable by Codex? |
|------|-------------|---------------------|
| `README.md` | Public-facing results and methodology | Yes |
| `AGENTS.md` | This documentation (for Codex) | Yes |
| `exitpoll_accuracy.csv` | Raw transcribed exit poll data (288 rows) | **Yes - source of truth** |
| `process_polls.py` | Processing script to generate harmonized CSV | Yes |
| `exitpoll_accuracy_harmonized.csv` | Generated output with scores | **No - regenerate instead** |
| `old/` | Archived original code-based extraction | No |

## Data Schema

### exitpoll_accuracy.csv (input)

```csv
election_id,election_name,election_date,state,total_seats,pollster,predictions_json,actual_results_json
```

- **election_id**: Unique identifier like `delhi_2025`, `maharashtra_2024`
- **election_date**: Date results were announced (YYYY-MM-DD)
- **predictions_json**: `{"Party": [min, max], ...}` - single values as `[x, x]`
- **actual_results_json**: `{"Party": seats, ...}`

### exitpoll_accuracy_harmonized.csv (output)

Additional columns added by `process_polls.py`:

| Column | Description |
|--------|-------------|
| pollster_harmonized | Canonical pollster name (e.g., "Axis My India" not "India Today-Axis My India") |
| predictions_json_harmonized | Predictions with single values expanded to ranges |
| intervalscore | Winkler interval score, normalized (lower = better) |
| winner_correct | 1 if predicted winner matches actual, 0 otherwise |
| abserror | Avg of |midpoint - actual| / total_seats across parties (lower = better) |
| predicted_winner | Party with highest midpoint in predictions |
| actual_winner | Party with most seats |

## How to Add New Elections

1. Find the Wikipedia page for the election (e.g., "2024 Maharashtra Legislative Assembly election")
2. Download HTML: `curl -A "Mozilla/5.0" "URL" > /tmp/election.html`
3. Read the HTML and find the exit poll table
4. Transcribe each pollster's predictions into CSV format
5. Append rows to `exitpoll_accuracy.csv`
6. Run `python3 process_polls.py` to regenerate harmonized output

### Transcription Rules

- **Ranges**: "35-40", "35 to 40", "35–40" all become `[35, 40]`
- **Single values**: "54" becomes `[54, 54]`
- **Party names**: Use shortened forms (BJP, INC, AAP) not full names
- **Alliances**: Use the alliance name from Wikipedia (NDA, UPA, INDIA, etc.)
- **Others**: Group small parties/independents as "Others" when Wikipedia does

### Party Name Shortening

| Short | Full Name |
|-------|-----------|
| BJP | Bharatiya Janata Party |
| INC | Indian National Congress |
| AAP | Aam Aadmi Party |
| TMC/AITC | Trinamool Congress |
| SP | Samajwadi Party |
| BSP | Bahujan Samaj Party |
| BJD | Biju Janata Dal |
| BRS | Bharat Rashtra Samithi |
| NDA | National Democratic Alliance (BJP-led) |
| UPA | United Progressive Alliance (INC-led) |
| INDIA | Indian National Developmental Inclusive Alliance |

## Processing Script

Run: `python3 process_polls.py`

### What It Does

1. **Pollster harmonization**: Maps variant names to canonical names
   - "India Today-Axis My India" → "Axis My India"
   - "P-MARQ", "Politique Marquer" → "P-Marq"
   - "ABP-CVoter", "Times Now-CVoter" → "CVoter"

2. **Range expansion**: Single-value predictions `[x, x]` are expanded to ranges **only if ALL of a pollster's predictions in that election are single values**. If even one prediction has a range, all their predictions are left as-is (they understand what they're doing). Expansion uses the average width of other pollsters for the same party in that election

3. **Scoring**: Calculates accuracy metrics for each poll

### Accuracy Metrics

- **intervalscore**: Winkler interval score. For each party that won ≥1 seat: if actual is in range, score = width; if outside, score = width + (2/α)×distance. Aggregated as `(1 / (total_seats × num_parties)) × sum(scores)`. Lower is better. Penalizes wide ranges and misses. Uses α=0.5 by default.

- **winner_correct**: Binary (1/0) - did the poll correctly predict which party would win the most seats?

- **abserror**: Average of `|midpoint - actual| / total_seats` across parties. Lower is better. Measures how close seat predictions were to actual results, normalized by legislature size. A value of 0.05 means predictions are off by 5% of total seats on average.

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

### Wikipedia Fetching

- Wikipedia blocks requests without User-Agent header (403 error)
- Use: `curl -A "Mozilla/5.0" "URL" > file.html`
- WebFetch tool may also work but curl is more reliable
- Downloaded files in `/tmp` may be deleted - re-download if needed

### Common Issues

1. **Colspan/rowspan in tables**: Party headers often span multiple columns
2. **Multiple exit poll tables**: Some pages have separate tables for different phases
3. **Missing data**: Some pollsters don't predict all parties - only transcribe what's shown
4. **Combined categories**: Sometimes "AAP+Others" is shown as one number - transcribe as shown

### Why Direct Transcription?

The original approach used BeautifulSoup + LLM to parse HTML automatically. This had issues:
- Artificially expanded single values into ranges (±3 seats)
- Misaligned columns due to colspan handling
- Inconsistent party name extraction

Direct human-guided transcription is more accurate and transparent.

## Important Reminders

1. **Always run `python3 process_polls.py`** after editing `exitpoll_accuracy.csv`
2. **Never edit `exitpoll_accuracy_harmonized.csv` directly** - it will be overwritten
3. **Check Wikipedia for exit poll tables** - they're usually in a section called "Exit polls"
4. **Use election result date** (not voting date) for `election_date` field

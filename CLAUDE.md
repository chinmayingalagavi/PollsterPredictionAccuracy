# Indian Election Poll Accuracy Tracker

## Goal

Evaluate Indian election pollster accuracy by comparing exit poll predictions against actual results.

## Architecture

```
Wikipedia HTML → BeautifulSoup (tables) + LLM (metadata) → Structured JSON → CSV
```

**Key learning:** LLMs struggle with table column alignment. Direct HTML table parsing with BeautifulSoup is more reliable for extracting exit poll data. Use LLM only for unstructured metadata (election name, date, actual results).

## Data Schema

### Election
```json
{
  "election_id": "delhi_2025",
  "election_name": "2025 Delhi Legislative Assembly election",
  "election_date": "2025-02-05",
  "election_type": "state_assembly",
  "state": "Delhi",
  "total_seats": 70,
  "wikipedia_url": "...",
  "actual_results": {"BJP": 48, "AAP": 22, "INC": 0}
}
```

### ExitPoll
```json
{
  "election_id": "delhi_2025",
  "pollster": "Axis My India",
  "predictions": {"BJP": [45, 55], "AAP": [15, 25], "INC": [0, 1]}
}
```

## Party Name Normalization

| Canonical | Aliases |
|-----------|---------|
| BJP | Bharatiya Janata Party |
| INC | Congress, Indian National Congress, CONG |
| AAP | Aam Aadmi Party |
| NDA | National Democratic Alliance |
| TMC | Trinamool Congress, AITC |
| SP | Samajwadi Party |
| BSP | Bahujan Samaj Party |
| SS | Shiv Sena (for Maharashtra) |
| NCP | Nationalist Congress Party |
| Others | Other, OTHERS, Ind, Independent |

## Elections Processed

1. https://en.wikipedia.org/wiki/2025_Delhi_Legislative_Assembly_election
2. https://en.wikipedia.org/wiki/2024_Maharashtra_Legislative_Assembly_election
3. https://en.wikipedia.org/wiki/2024_Jharkhand_Legislative_Assembly_election
4. https://en.wikipedia.org/wiki/2024_Haryana_Legislative_Assembly_election
5. https://en.wikipedia.org/wiki/2024_Jammu_and_Kashmir_Legislative_Assembly_election
6. https://en.wikipedia.org/wiki/2024_Andhra_Pradesh_Legislative_Assembly_election
7. https://en.wikipedia.org/wiki/2024_Odisha_Legislative_Assembly_election
8. https://en.wikipedia.org/wiki/2020_Delhi_Legislative_Assembly_election

## Accuracy Metrics

For each exit poll compute:
- `in_range_score`: per party, if actual falls within [min, max], add (actual_seats)/(max - min). Divide by number of parties. This weights accuracy by seat count—getting major parties right matters more than trivial "Others: 0" predictions.
- `winner_correct`: did poll predict the correct winning party?

## Known Issues

- Exit polls vs opinion polls: extract only exit polls (conducted after voting)
- Range formats vary: "35-40", "35 to 40", "35–40" — normalize to [min, max]
- Pollster name variations: "India Today-Axis My India" vs "Axis My India" — keep as-is for now

## Implementation Notes (Lessons Learned)

### Wikipedia Table Parsing

1. **Don't rely on LLM for table parsing** - LLMs misalign columns when parsing tables from raw text. Use BeautifulSoup to parse HTML tables directly.

2. **Table structure varies by election:**
   - Delhi 2025: Party headers in row 1 (row 0 just has "Polling Agency")
   - Maharashtra 2024: Party headers in row 0 with colspan
   - Delhi 2020: Multiple exit poll tables on same page

3. **Detect exit poll tables by checking first 2 rows for:**
   - Keywords: "polling", "agency", "pollster"
   - Party names: "bjp", "aap", "inc", "nda", "maha", etc.

4. **Alliance/party names to preserve (don't normalize):**
   - Maharashtra: "Maha Yuti", "Maha Vikas Aghadi"
   - Andhra Pradesh: "YSRCP", "Kutami" (TDP-led alliance)
   - Jharkhand: "MGB" (JMM-led alliance)
   - J&K: "INDIA" alliance
   - General: "NDA", "BJP+", "INC+"

### API Notes

- Wikipedia blocks requests without User-Agent header
- Use `{"User-Agent": "ProjectName/1.0 (educational)"}`
- OpenAI model: gpt-5.2 for metadata extraction

### Results Summary (8 elections processed)

| Election | Polls | Winner Accuracy | Notes |
|----------|-------|-----------------|-------|
| Delhi 2025 | 17 | 82% (14/17) | BJP surprised |
| Maharashtra 2024 | 13 | 84% (11/13) | Maha Yuti landslide |
| Jharkhand 2024 | 9 | 33% (3/9) | MGB won, pollsters failed |
| Haryana 2024 | 8 | 25% (2/8) | BJP surprise win |
| J&K 2024 | 5 | 100% (5/5) | INDIA alliance |
| Andhra Pradesh 2024 | 6 | 66% (4/6) | TDP-led Kutami won |
| Odisha 2024 | 2 | 50% (1/2) | BJP won |
| Delhi 2020 | 15 | 100% (15/15) | AAP dominant |

**Key insight:** Pollsters struggled most with Haryana 2024 (25%) and Jharkhand 2024 (33%) where results surprised everyone.

### Files

- `extractor.py` - Main extraction script
- `poll_accuracy.csv` - Output data
- `.env` - OpenAI API key (not committed)

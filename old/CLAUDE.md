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

## Elections Processed (22)

Elections are defined in `ELECTIONS` dict in extractor.py with canonical IDs:

| ID | State | Year |
|----|-------|------|
| delhi_2025 | Delhi | 2025 |
| maharashtra_2024 | Maharashtra | 2024 |
| jharkhand_2024 | Jharkhand | 2024 |
| haryana_2024 | Haryana | 2024 |
| jammu_kashmir_2024 | J&K | 2024 |
| andhra_pradesh_2024 | Andhra Pradesh | 2024 |
| odisha_2024 | Odisha | 2024 |
| arunachal_pradesh_2024 | Arunachal Pradesh | 2024 |
| sikkim_2024 | Sikkim | 2024 |
| karnataka_2023 | Karnataka | 2023 |
| chhattisgarh_2023 | Chhattisgarh | 2023 |
| rajasthan_2023 | Rajasthan | 2023 |
| madhya_pradesh_2023 | Madhya Pradesh | 2023 |
| telangana_2023 | Telangana | 2023 |
| mizoram_2023 | Mizoram | 2023 |
| meghalaya_2023 | Meghalaya | 2023 |
| tripura_2023 | Tripura | 2023 |
| nagaland_2023 | Nagaland | 2023 |
| gujarat_2022 | Gujarat | 2022 |
| himachal_pradesh_2022 | Himachal Pradesh | 2022 |
| punjab_2022 | Punjab | 2022 |
| uttar_pradesh_2022 | Uttar Pradesh | 2022 |

## Accuracy Metrics

For each exit poll compute:
- `in_range_score`: per party, if actual falls within [min, max], add (actual_seats)/(max - min). Divide by number of parties. This weights accuracy by seat count—getting major parties right matters more than trivial "Others: 0" predictions.
- `winner_correct`: did poll predict the correct winning party?

## Known Issues

- Exit polls vs opinion polls: extract only exit polls (conducted after voting)
- Range formats vary: "35-40", "35 to 40", "35–40" — normalize to [min, max]
- Pollster name variations: harmonized via `pollster_harmonize.py`

## Implementation Notes (Lessons Learned)

### Election IDs

**Always define election IDs explicitly** in the `ELECTIONS` dict rather than relying on LLM-generated IDs. This ensures:
- Consistent ID format across runs
- Reliable incremental processing (skip already-processed elections)
- No ID format mismatches between URL and CSV

### Wikipedia Table Parsing

1. **Don't rely on LLM for table parsing** - LLMs misalign columns when parsing tables from raw text. Use BeautifulSoup to parse HTML tables directly.

2. **Table structure varies by election:**
   - Delhi 2025: Party headers in row 1 (row 0 just has "Polling Agency")
   - Maharashtra 2024: Party headers in row 0 with colspan
   - Nagaland/Meghalaya: Party headers in row 1, row 0 has empty cells
   - Delhi 2020: Multiple exit poll tables on same page

3. **Detect exit poll tables by checking first 2 rows for:**
   - Keywords: "polling", "agency", "pollster"
   - Party names from `party_keywords` list

4. **party_keywords must include regional parties:**
   - National: bjp, aap, inc, congress, nda, sp, bsp, tmc, ncp
   - Maharashtra: maha, yuti, vikas
   - South: ysrcp, tdp, kutami, dmk, aiadmk
   - East: jmm, bjd, mgb
   - J&K: jkpdp, jknc, india
   - **Northeast (critical!):** npp, neda, npf, udp, aitc, ndpp, mnf, zpm, ipft, tipra, vpp

5. **Alliance/party names to preserve (don't normalize):**
   - Maharashtra: "Maha Yuti", "Maha Vikas Aghadi"
   - Andhra Pradesh: "YSRCP", "Kutami" (TDP-led alliance)
   - Jharkhand: "MGB" (JMM-led alliance)
   - J&K: "INDIA" alliance
   - Nagaland: "NEDA" (North East Democratic Alliance)
   - Meghalaya: "NPP" (National People's Party)
   - General: "NDA", "BJP+", "INC+"

### OpenAI API

- **Structured Outputs:** Use `client.responses.parse()` with Pydantic models for reliable metadata extraction
- **Model:** gpt-5.2 for metadata extraction
- **Rate limits:** Implement exponential backoff (2^attempt + 1 seconds)
- Wikipedia blocks requests without User-Agent header: `{"User-Agent": "ProjectName/1.0 (educational)"}`

### Incremental CSV Processing

- `get_processed_elections()` reads existing CSV and returns set of election_ids
- `append_to_csv()` appends new results one election at a time
- Match by exact election_id (not URL pattern matching)
- Always use canonical election IDs from ELECTIONS dict

### Pollster Name Harmonization

Pollster names vary across elections (e.g., "India Today-Axis My India" vs "Axis My India"). Use `pollster_harmonize.py` module with:
- `harmonize_pollster(name)` - normalize to canonical name
- `harmonize_csv_pollsters()` - post-process CSV to harmonize all names

### Files

- `extractor.py` - Main extraction script
- `pollster_harmonize.py` - Pollster name normalization
- `poll_accuracy.csv` - Output data (178 rows, 22 elections)
- `.env` - OpenAI API key (not committed)

# Indian Election Pollster Accuracy Tracker

Evaluates Indian election pollster accuracy by comparing exit poll predictions against actual results.

## How It Works

```
Wikipedia HTML → BeautifulSoup (tables) + LLM (metadata) → Structured JSON → CSV
```

- **BeautifulSoup** parses HTML tables directly (LLMs struggle with table column alignment)
- **OpenAI API** (gpt-5.2) extracts metadata only (election name, date, actual results)

## Accuracy Metrics

- **in_range_score**: If actual seats fall within predicted range, score = actual_seats / (max - min). Averaged across parties.
- **winner_correct**: Did the poll predict the winning party?

## Results (7 Elections)

| Election | Polls | Winner Accuracy |
|----------|-------|-----------------|
| Delhi 2025 | 17 | 82% |
| Maharashtra 2024 | 13 | 84% |
| Jharkhand 2024 | 9 | 33% |
| Haryana 2024 | 8 | 25% |
| J&K 2024 | 5 | 100% |
| Karnataka 2023 | - | - |
| Chhattisgarh 2023 | - | 8% |

**Key insight:** Pollsters struggled most with Haryana 2024 (25%) and Jharkhand 2024 (33%) — surprise results.

## Usage

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
python extractor.py
```

Output: `poll_accuracy.csv`

## Files

- `extractor.py` - Main extraction script
- `poll_accuracy.csv` - Output data
- `requirements.txt` - Dependencies

---

*Vibecoded with Claude Opus 4.5*

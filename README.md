# Indian Election Pollster Accuracy Tracker

Evaluates Indian election pollster accuracy by comparing exit poll predictions against actual results.

## Pollster Rankings (2+ polls)

| Pollster | Polls | Avg Score | Winner Accuracy |
|----------|-------|-----------|-----------------|
| India Today-Axis My India | 2 | 1.44 | 50% (1/2) |
| Axis My India | 4 | 1.16 | 100% (4/4) |
| Poll Diary | 2 | 1.14 | 100% (2/2) |
| Today's Chanakya | 2 | 0.73 | 100% (2/2) |
| Poll of Polls | 3 | 0.60 | 67% (2/3) |
| JVC | 2 | 0.31 | 100% (2/2) |
| People's Insight | 6 | 0.22 | 83% (5/6) |
| Dainik Bhaskar | 4 | 0.09 | 0% (0/4) |
| Matrize | 4 | 0.05 | 50% (2/4) |
| Chanakya Strategies | 2 | 0.00 | 50% (1/2) |
| People's Pulse | 2 | 0.00 | 50% (1/2) |
| Electoral Edge | 2 | 0.00 | 50% (1/2) |
| India TV-CNX | 2 | 0.00 | 50% (1/2) |
| Times Now-ETG | 2 | 0.00 | 50% (1/2) |

**Key finding:** Axis My India leads with 100% winner accuracy across 4 elections and a 1.16 avg score.

## How It Works

```
Wikipedia HTML → BeautifulSoup (tables) + LLM (metadata) → Structured JSON → CSV
```

- **BeautifulSoup** parses HTML tables directly (LLMs struggle with table column alignment)
- **OpenAI Structured Outputs** with Pydantic extracts election metadata

## Accuracy Metrics

- **Avg Score**: If actual seats fall within predicted range, score = actual_seats / (max - min). Averaged across parties.
- **Winner Accuracy**: Did the poll predict the winning party?

## Elections Analyzed (7)

Delhi 2025, Maharashtra 2024, Jharkhand 2024, Haryana 2024, J&K 2024, Karnataka 2023, Chhattisgarh 2023

## Usage

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
python extractor.py
```

Output: `poll_accuracy.csv`

---

*Vibecoded with Claude Opus 4.5*

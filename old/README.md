# Indian Election Pollster Accuracy Tracker

Evaluates Indian election pollster accuracy by comparing exit poll predictions against actual results.

## Pollster Rankings (2+ polls)

| Pollster | Polls | Avg Score | Winner Accuracy |
|----------|-------|-----------|-----------------|
| Poll Diary | 2 | 1.14 | 100% (2/2) |
| Matrize | 17 | 0.98 | 47% (8/17) |
| Jan Ki Baat | 11 | 0.95 | 45% (5/11) |
| Axis My India | 19 | 0.73 | 78% (15/19) |
| P-Marq | 9 | 0.72 | 77% (7/9) |
| Today's Chanakya | 11 | 0.60 | 63% (7/11) |
| ETG | 13 | 0.57 | 38% (5/13) |
| People's Pulse | 7 | 0.51 | 71% (5/7) |
| People's Insight | 8 | 0.50 | 87% (7/8) |
| Poll of Polls | 6 | 0.39 | 83% (5/6) |
| CVoter | 17 | 0.24 | 52% (9/17) |
| Polstrat | 10 | 0.23 | 80% (8/10) |
| Dainik Bhaskar | 7 | 0.19 | 28% (2/7) |

**Key finding:** Axis My India leads with 19 polls and 78% winner accuracy. People's Insight has the highest winner accuracy (87%) among pollsters with 5+ polls.

## How It Works

```
Wikipedia HTML → BeautifulSoup (tables) + LLM (metadata) → Structured JSON → CSV
```

- **BeautifulSoup** parses HTML tables directly (LLMs struggle with table column alignment)
- **OpenAI Structured Outputs** with Pydantic extracts election metadata

## Accuracy Metrics

- **Avg Score**: If actual seats fall within predicted range, score = actual_seats / (max - min). Averaged across parties.
- **Winner Accuracy**: Did the poll predict the winning party?

## Elections Analyzed (20)

**2024-25:** Delhi, Maharashtra, Jharkhand, Haryana, J&K, Andhra Pradesh, Odisha

**2023:** Karnataka, Chhattisgarh, Rajasthan, Madhya Pradesh, Telangana, Mizoram, Meghalaya, Tripura, Nagaland

**2022:** Gujarat, Himachal Pradesh, Punjab, Uttar Pradesh

## Usage

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
python extractor.py
```

Output: `poll_accuracy.csv`

---

*Vibecoded with Claude Opus 4.5*

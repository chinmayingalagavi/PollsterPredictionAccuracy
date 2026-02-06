"""
Indian Election Poll Accuracy Tracker
Extracts election results and exit poll data from Wikipedia using OpenAI.
"""

import csv
import json
import re
import time
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
import requests
from openai import OpenAI, RateLimitError

from pollster_harmonize import harmonize_pollster

MODEL = 'gpt-5.2'

load_dotenv()  # Load .env file


# Pydantic model for structured election metadata extraction
class ElectionMetadata(BaseModel):
    election_id: str
    election_name: str
    election_date: str
    election_type: str
    state: str
    total_seats: int
    actual_results: Optional[dict[str, int]]


# Party name normalization mapping
PARTY_ALIASES = {
    "Bharatiya Janata Party": "BJP",
    "Indian National Congress": "INC",
    "Congress": "INC",
    "CONG": "INC",
    "Aam Aadmi Party": "AAP",
    "National Democratic Alliance": "NDA", 
    "Trinamool Congress": "TMC",
    "AITC": "TMC",
    "Samajwadi Party": "SP",
    "Bahujan Samaj Party": "BSP",
    "Shiv Sena": "SS",
    "Nationalist Congress Party": "NCP",
    "Other": "Others",
    "OTHERS": "Others",
    "Ind": "Independent"
}

# Non-pollster rows to filter out
NON_POLLSTER_KEYWORDS = [
    "average", "actual result", "actual results", "final result", "final results",
    "result", "election result", "seat tally", "seats won", "total"
]

EXTRACTION_PROMPT = """You are analyzing a Wikipedia page about an Indian election. Extract the following information in JSON format:

1. **Election Details**:
   - election_id: lowercase format like "delhi_2025" or "maharashtra_2024"
   - election_name: full name like "2025 Delhi Legislative Assembly election"
   - election_date: in YYYY-MM-DD format
   - election_type: "state_assembly" or "general"
   - state: state name
   - total_seats: total number of seats contested
   - actual_results: dictionary mapping party/alliance names to seats won

2. **Exit Polls** (NOT opinion polls - only polls conducted AFTER voting):
   - For each exit poll, extract:
     - pollster: name of the polling organization
     - predictions: dictionary mapping party/alliance names to [min, max] seat predictions
   - Normalize ranges like "35-40", "35 to 40", "35–40" to [35, 40]
   - If a single number is given, use [n, n]
   - CRITICAL: Match the column headers EXACTLY. The first data column after pollster name goes with the first party/alliance header, second with second, etc.

Return ONLY valid JSON in this exact format:
{
  "election": {
    "election_id": "...",
    "election_name": "...",
    "election_date": "YYYY-MM-DD",
    "election_type": "state_assembly",
    "state": "...",
    "total_seats": 70,
    "actual_results": {"PartyA": 48, "PartyB": 22}
  },
  "exit_polls": [
    {
      "pollster": "Pollster Name",
      "predictions": {"PartyA": [45, 55], "PartyB": [15, 25]}
    }
  ]
}

Important:
- Use party/alliance names EXACTLY as they appear in exit poll table headers (e.g., "Maha Yuti", "Maha Vikas Aghadi", "AAP", "BJP")
- For actual_results, use the same names as exit polls when possible for consistency
- Only include EXIT polls, not opinion polls
- Ensure all seat numbers are integers
- If actual results are not yet available, set actual_results to null
- Ignore "Lead" columns - only extract seat predictions
"""


def fetch_wikipedia_page(url: str) -> str:
    """Fetch Wikipedia page and extract main content as clean text."""
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "ElectionPollTracker/1.0 (educational project)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Get main content area only
    content = soup.find('div', {'id': 'mw-content-text'})
    if not content:
        content = soup.find('body')

    # Remove non-essential elements
    for tag in content.find_all(['script', 'style', 'nav', 'sup', 'span.mw-editsection']):
        tag.decompose()

    # Extract text with table structure preserved
    text = content.get_text(separator=' | ', strip=True)

    return text


def _clean_cell_text(text: str) -> str:
    """Clean table cell text for consistent header/pollster parsing."""
    if text is None:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\[[^\]]+\]", "", text)  # Remove citation markers like [1], [a]
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_range_text(text: str) -> str:
    """Normalize a range cell for parsing numeric values."""
    text = _clean_cell_text(text)
    text = re.sub(r"\(.*?\)", "", text)  # Drop parenthetical notes
    return text.strip()


def parse_range(text: str) -> list:
    """Parse a range string like '147-157' or '147–157' into [min, max]."""
    text = _clean_range_text(text)
    if not text or text.lower() in ['hung', '-', '–', '']:
        return None

    # Normalize dash variants for regex
    text = text.replace("−", "-").replace("–", "-")

    # Range with separators
    range_match = re.search(r"(\d[\d,]*)\s*(?:-|to)\s*(\d[\d,]*)", text, flags=re.IGNORECASE)
    if range_match:
        try:
            low = int(range_match.group(1).replace(",", ""))
            high = int(range_match.group(2).replace(",", ""))
            return [low, high]
        except ValueError:
            return None

    # Single number (optionally with +)
    single_match = re.fullmatch(r"\s*\d[\d,]*\s*\+?\s*", text)
    if single_match:
        try:
            n = int(re.search(r"\d[\d,]*", text).group(0).replace(",", ""))
            return [n, n]
        except ValueError:
            return None

    return None


def _table_to_grid(table) -> list:
    """Convert an HTML table to a 2D grid, expanding rowspan/colspan."""
    rows = []
    spans = {}  # col_idx -> [rows_remaining, text]

    def _safe_span(value) -> int:
        if value is None:
            return 1
        try:
            return int(value)
        except (TypeError, ValueError):
            match = re.search(r"\d+", str(value))
            return int(match.group(0)) if match else 1

    for row in table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue

        grid_row = []
        col_idx = 0

        def fill_spans():
            nonlocal col_idx
            while col_idx in spans:
                grid_row.append(spans[col_idx][1])
                spans[col_idx][0] -= 1
                if spans[col_idx][0] <= 0:
                    del spans[col_idx]
                col_idx += 1

        fill_spans()

        for cell in cells:
            fill_spans()
            text = _clean_cell_text(cell.get_text(" ", strip=True))
            rowspan = _safe_span(cell.get("rowspan", 1))
            colspan = _safe_span(cell.get("colspan", 1))

            for _ in range(colspan):
                grid_row.append(text)
                if rowspan > 1:
                    spans[col_idx] = [rowspan - 1, text]
                col_idx += 1

        if spans:
            max_span_col = max(spans.keys())
            while col_idx <= max_span_col:
                if col_idx in spans:
                    grid_row.append(spans[col_idx][1])
                    spans[col_idx][0] -= 1
                    if spans[col_idx][0] <= 0:
                        del spans[col_idx]
                else:
                    grid_row.append("")
                col_idx += 1

        rows.append(grid_row)

    return rows


def extract_exit_polls_from_table(url: str) -> list:
    """Extract exit polls by directly parsing Wikipedia HTML tables."""
    from bs4 import BeautifulSoup

    headers_req = {"User-Agent": "ElectionPollTracker/1.0 (educational project)"}
    response = requests.get(url, headers=headers_req, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    exit_polls = []

    # Find all wikitables
    for table in soup.find_all('table', class_='wikitable'):
        grid_rows = _table_to_grid(table)
        if len(grid_rows) < 3:
            continue

        # Check first two rows for exit poll table indicators
        first_two_rows_text = ' '.join([
            cell.lower()
            for row in grid_rows[:2]
            for cell in row
        ])

        is_exit_poll_table = (
            ('polling' in first_two_rows_text or 'pollster' in first_two_rows_text or 'agency' in first_two_rows_text) and
            any(x in first_two_rows_text for x in ['bjp', 'aap', 'inc', 'nda', 'maha', 'congress', 'lead',
                                                    'ysrcp', 'tdp', 'kutami', 'jmm', 'bjd', 'india', 'mgb',
                                                    'npp', 'neda', 'npf', 'udp', 'mnf', 'zpm', 'tipra'])
        )

        if not is_exit_poll_table:
            continue

        party_keywords = ['bjp', 'aap', 'inc', 'congress', 'nda', 'maha', 'yuti', 'vikas', 'others', 'sp', 'bsp',
                          'ysrcp', 'tdp', 'kutami', 'india', 'jmm', 'bjd', 'rjd', 'jdu', 'tmc', 'dmk', 'aiadmk',
                          'cpim', 'cpi', 'jkpdp', 'jknc', 'mgb', 'ncp', 'ss', 'shivsena',
                          # Northeast India parties
                          'npp', 'neda', 'npf', 'udp', 'aitc', 'ndpp', 'mpa', 'vpp', 'mnf', 'zpm', 'ipft', 'tipra']
        subheader_ignore = ['lead', 'margin', 'swing', 'vote share', 'votes', 'vote', '%']

        # Identify pollster column from header rows
        pollster_col_idx = None
        for row in grid_rows[:3]:
            for idx, text in enumerate(row):
                text_lower = text.lower()
                if any(k in text_lower for k in ['polling agency', 'pollster', 'polling organisation', 'polling organization', 'agency']):
                    pollster_col_idx = idx
                    break
            if pollster_col_idx is not None:
                break
        if pollster_col_idx is None:
            pollster_col_idx = 0

        # Find party header row (row with >=2 party names)
        header_row_idx = None
        for row_idx in range(min(3, len(grid_rows))):
            row_texts = grid_rows[row_idx]
            has_parties = sum(1 for t in row_texts if any(k in t.lower() for k in party_keywords)) >= 2
            if has_parties:
                header_row_idx = row_idx
                break

        if header_row_idx is None:
            continue

        # Build party columns based on header row
        party_columns = {}
        for col_idx, text in enumerate(grid_rows[header_row_idx]):
            text_lower = text.lower()
            if col_idx == pollster_col_idx:
                continue
            if text_lower in ['lead', 'polling agency', 'pollster', 'date published', '', 'ref.', 'ref']:
                continue
            if any(k in text_lower for k in party_keywords) or text_lower == 'others':
                party_columns[col_idx] = text

        if not party_columns:
            continue

        # If next row is a subheader row (Seats/Lead/Vote share), drop non-seat columns
        data_start_row = header_row_idx + 1
        if data_start_row < len(grid_rows):
            subheader_row = grid_rows[data_start_row]
            subheader_hits = sum(1 for t in subheader_row if any(k in t.lower() for k in subheader_ignore))
            if subheader_hits >= 2:
                for col_idx, text in enumerate(subheader_row):
                    if any(k in text.lower() for k in subheader_ignore):
                        party_columns.pop(col_idx, None)
                data_start_row += 1
            else:
                # Pure "Seats" subheader row (no extra columns)
                non_empty = [t.lower().strip() for t in subheader_row if t.strip()]
                if non_empty and all(t in ['seat', 'seats'] for t in non_empty):
                    data_start_row += 1

        if not party_columns:
            continue

        print(f"  Found exit poll table with party columns: {list(party_columns.values())}")

        # Parse data rows
        for row in grid_rows[data_start_row:]:
            if pollster_col_idx >= len(row):
                continue
            pollster = row[pollster_col_idx]
            if not pollster:
                continue
            pollster = pollster.strip()
            pollster_lower = pollster.lower()

            # Skip header-like rows
            if pollster_lower in ['polling agency', 'pollster', 'date published', '']:
                continue

            # Filter out non-pollster rows (Average, Actual Result, etc.)
            if any(keyword in pollster_lower for keyword in NON_POLLSTER_KEYWORDS):
                continue

            # Extract predictions
            predictions = {}
            for col_idx, party in party_columns.items():
                if col_idx >= len(row):
                    continue
                range_val = parse_range(row[col_idx])
                if range_val:
                    predictions[party] = range_val

            if predictions:
                exit_polls.append({
                    "pollster": pollster,
                    "predictions": predictions
                })

    # Deduplicate exit polls by pollster name (keep first occurrence)
    seen_pollsters = set()
    unique_polls = []
    for poll in exit_polls:
        pollster_key = poll["pollster"].lower().strip()
        if pollster_key not in seen_pollsters:
            seen_pollsters.add(pollster_key)
            unique_polls.append(poll)

    return unique_polls


METADATA_PROMPT = """Extract election metadata from this Wikipedia page about an Indian state assembly election.

For actual_results, use the same party/alliance names as used in exit poll tables on the page.
For Maharashtra, use "Maha Yuti" and "Maha Vikas Aghadi" as alliance names.
If results are not yet available, set actual_results to null."""


def extract_election_data(url: str, model: str = MODEL) -> dict:
    """
    Extract election data using direct HTML parsing for tables + LLM for metadata.
    Uses OpenAI Structured Outputs with Pydantic for reliable metadata extraction.
    """
    client = OpenAI()

    print(f"Fetching {url}...")

    # Step 1: Extract exit polls directly from HTML tables
    print("  Parsing exit poll tables directly...")
    exit_polls = extract_exit_polls_from_table(url)
    print(f"  Found {len(exit_polls)} exit polls from tables")

    # Step 2: Use LLM with Structured Outputs for election metadata
    page_text = fetch_wikipedia_page(url)
    max_chars = 50000  # Smaller since we only need metadata
    if len(page_text) > max_chars:
        page_text = page_text[:max_chars]

    print(f"  Sending to {model} for metadata extraction (Structured Outputs)...")

    # Retry with exponential backoff for rate limits
    for attempt in range(5):
        try:
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": METADATA_PROMPT},
                    {"role": "user", "content": f"Extract election metadata:\n\n{page_text}"}
                ],
                text_format=ElectionMetadata,
            )
            break
        except RateLimitError as e:
            wait_time = 2 ** attempt + 1
            print(f"  Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
    else:
        raise Exception("Failed after 5 retries due to rate limiting")

    election = response.output_parsed.model_dump()
    election["wikipedia_url"] = url

    return {
        "election": election,
        "exit_polls": exit_polls
    }


def normalize_party_names(data: dict) -> dict:
    """Normalize party names to canonical abbreviations."""

    def normalize(name: str) -> str:
        return PARTY_ALIASES.get(name, name)

    # Normalize actual_results
    if data.get("election", {}).get("actual_results"):
        normalized = {}
        for party, seats in data["election"]["actual_results"].items():
            normalized[normalize(party)] = seats
        data["election"]["actual_results"] = normalized

    # Normalize exit poll predictions
    for poll in data.get("exit_polls", []):
        if poll.get("predictions"):
            normalized = {}
            for party, range_val in poll["predictions"].items():
                normalized[normalize(party)] = range_val
            poll["predictions"] = normalized

    return data


def harmonize_pollster_names(data: dict) -> dict:
    """Harmonize pollster names via a manual alias dictionary."""
    exit_polls = data.get("exit_polls", [])
    for poll in exit_polls:
        poll["pollster"] = harmonize_pollster(poll.get("pollster", ""))

    # Deduplicate again after harmonization (keep first occurrence).
    seen = set()
    unique = []
    for poll in exit_polls:
        key = poll.get("pollster", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(poll)

    data["exit_polls"] = unique
    return data


def expand_point_estimates(exit_polls: list) -> list:
    """
    Expand point estimates [n, n] to ranges based on average range width from other pollsters.
    For each party, calculate the average range width from pollsters that gave ranges,
    then expand point estimates using that width (centered on the point).
    """
    if not exit_polls:
        return exit_polls

    # Collect all parties and their range widths (excluding point estimates)
    party_widths = {}  # party -> list of widths

    for poll in exit_polls:
        for party, pred in poll.get("predictions", {}).items():
            if pred and len(pred) == 2:
                width = pred[1] - pred[0]
                if width > 0:  # Not a point estimate
                    if party not in party_widths:
                        party_widths[party] = []
                    party_widths[party].append(width)

    # Calculate average width per party
    avg_widths = {}
    for party, widths in party_widths.items():
        if widths:
            avg_widths[party] = sum(widths) / len(widths)

    # Calculate overall average width as fallback
    all_widths = [w for widths in party_widths.values() for w in widths]
    overall_avg = sum(all_widths) / len(all_widths) if all_widths else 10  # Default to 10 if no ranges

    # Expand point estimates
    for poll in exit_polls:
        for party, pred in poll.get("predictions", {}).items():
            if pred and len(pred) == 2 and pred[0] == pred[1]:
                # This is a point estimate - expand it
                point = pred[0]
                width = avg_widths.get(party, overall_avg)
                half_width = int(width / 2)
                # Ensure range doesn't go below 0
                new_min = max(0, point - half_width)
                new_max = point + half_width
                poll["predictions"][party] = [new_min, new_max]

    return exit_polls


def filter_unrealistic_predictions(exit_polls: list, total_seats: int) -> list:
    """
    Filter out predictions that exceed total seats (likely parsing errors
    where vote counts were picked up instead of seat predictions).
    """
    if not exit_polls or not total_seats:
        return exit_polls

    filtered = []
    for poll in exit_polls:
        valid_predictions = {}
        invalid_found = False
        for party, pred in poll.get("predictions", {}).items():
            if pred and len(pred) == 2:
                # Keep prediction only if both values are <= total_seats
                if pred[0] <= total_seats and pred[1] <= total_seats:
                    valid_predictions[party] = pred
                else:
                    invalid_found = True
                    break

        if invalid_found:
            continue

        if valid_predictions:
            filtered.append({
                "pollster": poll["pollster"],
                "predictions": valid_predictions
            })

    return filtered


def compute_accuracy_metrics(election: dict, exit_polls: list) -> list:
    """
    Compute accuracy metrics for each exit poll.

    Metrics:
    - in_range_score: For each party, if actual falls within [min, max],
      add (actual_seats)/(max-min) to score. Divide by number of parties.
      This weights accuracy by seat count - getting major parties right matters more.
    - winner_correct: Did poll predict the correct winning party?
    """
    actual_results = election.get("actual_results")
    if not actual_results:
        return []

    # Find actual winner
    actual_winner = max(actual_results.items(), key=lambda x: x[1])[0]

    results = []
    for poll in exit_polls:
        predictions = poll.get("predictions", {})
        if not predictions:
            continue

        # Compute in_range score - weighted by actual seats
        parties_evaluated = set(predictions.keys()) | set(k for k, v in actual_results.items() if v > 0)

        score_sum = 0
        party_scores = {}

        for party in parties_evaluated:
            actual = actual_results.get(party, 0)
            pred_range = predictions.get(party)

            if pred_range:
                min_pred, max_pred = pred_range
                if min_pred <= actual <= max_pred:
                    # Score: actual_seats / (max - min), or actual_seats if range is 0
                    range_width = max_pred - min_pred
                    party_score = actual / range_width if range_width > 0 else float(actual)
                else:
                    party_score = 0.0
            else:
                party_score = 0.0  # Party not predicted

            party_scores[party] = party_score
            score_sum += party_score

        overall_score = score_sum / len(parties_evaluated) if parties_evaluated else 0

        # Check if winner was correctly predicted
        if predictions:
            # Find predicted winner (party with highest max prediction)
            # Filter out None values and "Others" (shouldn't be winner)
            valid_preds = {
                k: v for k, v in predictions.items()
                if v is not None and len(v) == 2 and k.lower() != "others"
            }
            if valid_preds:
                predicted_winner = max(valid_preds.items(), key=lambda x: x[1][1])[0]
                winner_correct = predicted_winner == actual_winner
            else:
                predicted_winner = None
                winner_correct = False
        else:
            predicted_winner = None
            winner_correct = False

        results.append({
            "pollster": poll["pollster"],
            "in_range_score": round(overall_score, 4),
            "party_scores": party_scores,
            "predicted_winner": predicted_winner,
            "actual_winner": actual_winner,
            "winner_correct": winner_correct
        })

    return results


def process_election(election_id: str, url: str, model: str = MODEL) -> dict:
    """Process a single election and compute metrics."""
    # Extract data
    data = extract_election_data(url, model=model)
    data = normalize_party_names(data)
    data = harmonize_pollster_names(data)

    # Override LLM-generated election_id with our canonical ID
    data["election"]["election_id"] = election_id

    # Expand point estimates to ranges based on average width
    data["exit_polls"] = expand_point_estimates(data.get("exit_polls", []))

    # Filter out unrealistic predictions (vote counts picked up instead of seats)
    total_seats = data["election"].get("total_seats", 300)
    data["exit_polls"] = filter_unrealistic_predictions(data["exit_polls"], total_seats)

    # Compute metrics
    metrics = compute_accuracy_metrics(data["election"], data.get("exit_polls", []))

    return {
        "election": data["election"],
        "exit_polls": data.get("exit_polls", []),
        "metrics": metrics
    }


def print_results(result: dict):
    """Pretty print the results."""
    election = result["election"]
    print(f"\n{'='*60}")
    print(f"Election: {election['election_name']}")
    print(f"Date: {election['election_date']}")
    print(f"State: {election['state']}")
    print(f"Total Seats: {election['total_seats']}")
    print(f"\nActual Results: {json.dumps(election.get('actual_results', {}), indent=2)}")

    print(f"\n{'='*60}")
    print("EXIT POLLS:")
    for poll in result["exit_polls"]:
        print(f"\n  {poll['pollster']}:")
        print(f"    Predictions: {json.dumps(poll['predictions'], indent=6)}")

    print(f"\n{'='*60}")
    print("ACCURACY METRICS:")
    for metric in result["metrics"]:
        print(f"\n  {metric['pollster']}:")
        print(f"    In-Range Score: {metric['in_range_score']:.4f}")
        print(f"    Winner Correct: {metric['winner_correct']} (Predicted: {metric['predicted_winner']}, Actual: {metric['actual_winner']})")
        print(f"    Party Scores: {json.dumps({k: round(v, 4) for k, v in metric['party_scores'].items()}, indent=6)}")


def get_processed_elections(filename: str = "poll_accuracy.csv") -> set:
    """Get set of election URLs already processed in the CSV."""
    import os
    if not os.path.exists(filename):
        return set()

    processed = set()
    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract election identifier from the data
            election_id = row.get("election_id", "")
            if election_id:
                processed.add(election_id)
    return processed


def append_to_csv(result: dict, filename: str = "poll_accuracy.csv"):
    """Append a single election result to CSV."""
    import os

    election = result["election"]
    rows = []

    for metric in result["metrics"]:
        poll_data = next(
            (p for p in result["exit_polls"] if p["pollster"] == metric["pollster"]),
            {}
        )
        predictions = poll_data.get("predictions", {})

        rows.append({
            "election_id": election["election_id"],
            "election_name": election["election_name"],
            "election_date": election["election_date"],
            "state": election["state"],
            "total_seats": election["total_seats"],
            "pollster": metric["pollster"],
            "in_range_score": metric["in_range_score"],
            "winner_correct": metric["winner_correct"],
            "predicted_winner": metric["predicted_winner"],
            "actual_winner": metric["actual_winner"],
            "predictions_json": json.dumps(predictions),
            "actual_results_json": json.dumps(election.get("actual_results", {})),
        })

    if not rows:
        return

    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    print(f"  Appended {len(rows)} rows to {filename}")


def harmonize_csv_pollsters(filename: str = "poll_accuracy.csv"):
    """Harmonize pollster names in an existing CSV in-place."""
    import os
    if not os.path.exists(filename):
        return

    with open(filename, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows or not fieldnames or "pollster" not in fieldnames:
        return

    changed = 0
    for row in rows:
        original = row.get("pollster", "")
        canonical = harmonize_pollster(original)
        if canonical != original:
            row["pollster"] = canonical
            changed += 1

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Harmonized pollster names in {filename} ({changed} row changes)")


def save_to_csv(all_results: list, filename: str = "poll_accuracy.csv"):
    """Save all election results to CSV."""
    rows = []
    for result in all_results:
        election = result["election"]
        for metric in result["metrics"]:
            # Find the poll data
            poll_data = next(
                (p for p in result["exit_polls"] if p["pollster"] == metric["pollster"]),
                {}
            )
            predictions = poll_data.get("predictions", {})

            rows.append({
                "election_id": election["election_id"],
                "election_name": election["election_name"],
                "election_date": election["election_date"],
                "state": election["state"],
                "total_seats": election["total_seats"],
                "pollster": metric["pollster"],
                "in_range_score": metric["in_range_score"],
                "winner_correct": metric["winner_correct"],
                "predicted_winner": metric["predicted_winner"],
                "actual_winner": metric["actual_winner"],
                "predictions_json": json.dumps(predictions),
                "actual_results_json": json.dumps(election.get("actual_results", {})),
            })

    if rows:
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved {len(rows)} rows to {filename}")


# Election ID -> Wikipedia URL mapping
ELECTIONS = {
    # 2025
    "delhi_2025": "https://en.wikipedia.org/wiki/2025_Delhi_Legislative_Assembly_election",
    # 2024
    "maharashtra_2024": "https://en.wikipedia.org/wiki/2024_Maharashtra_Legislative_Assembly_election",
    "jharkhand_2024": "https://en.wikipedia.org/wiki/2024_Jharkhand_Legislative_Assembly_election",
    "haryana_2024": "https://en.wikipedia.org/wiki/2024_Haryana_Legislative_Assembly_election",
    "jammu_kashmir_2024": "https://en.wikipedia.org/wiki/2024_Jammu_and_Kashmir_Legislative_Assembly_election",
    "andhra_pradesh_2024": "https://en.wikipedia.org/wiki/2024_Andhra_Pradesh_Legislative_Assembly_election",
    "odisha_2024": "https://en.wikipedia.org/wiki/2024_Odisha_Legislative_Assembly_election",
    "arunachal_pradesh_2024": "https://en.wikipedia.org/wiki/2024_Arunachal_Pradesh_Legislative_Assembly_election",
    "sikkim_2024": "https://en.wikipedia.org/wiki/2024_Sikkim_Legislative_Assembly_election",
    # 2023
    "karnataka_2023": "https://en.wikipedia.org/wiki/2023_Karnataka_Legislative_Assembly_election",
    "chhattisgarh_2023": "https://en.wikipedia.org/wiki/2023_Chhattisgarh_Legislative_Assembly_election",
    "rajasthan_2023": "https://en.wikipedia.org/wiki/2023_Rajasthan_Legislative_Assembly_election",
    "madhya_pradesh_2023": "https://en.wikipedia.org/wiki/2023_Madhya_Pradesh_Legislative_Assembly_election",
    "telangana_2023": "https://en.wikipedia.org/wiki/2023_Telangana_Legislative_Assembly_election",
    "mizoram_2023": "https://en.wikipedia.org/wiki/2023_Mizoram_Legislative_Assembly_election",
    "meghalaya_2023": "https://en.wikipedia.org/wiki/2023_Meghalaya_Legislative_Assembly_election",
    "tripura_2023": "https://en.wikipedia.org/wiki/2023_Tripura_Legislative_Assembly_election",
    "nagaland_2023": "https://en.wikipedia.org/wiki/2023_Nagaland_Legislative_Assembly_election",
    # 2022
    "gujarat_2022": "https://en.wikipedia.org/wiki/2022_Gujarat_Legislative_Assembly_election",
    "himachal_pradesh_2022": "https://en.wikipedia.org/wiki/2022_Himachal_Pradesh_Legislative_Assembly_election",
    "punjab_2022": "https://en.wikipedia.org/wiki/2022_Punjab_Legislative_Assembly_election",
    "uttar_pradesh_2022": "https://en.wikipedia.org/wiki/2022_Uttar_Pradesh_Legislative_Assembly_election",
}


if __name__ == "__main__":
    # Check which elections are already processed
    processed = get_processed_elections()
    print(f"Already processed: {len(processed)} elections")
    if processed:
        print(f"  IDs: {processed}")

    for election_id, url in ELECTIONS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {election_id}")

        # Check if already processed (exact ID match)
        if election_id in processed:
            print(f"  Skipping - already processed")
            continue

        try:
            result = process_election(election_id, url)
            print_results(result)
            append_to_csv(result)
            # Add to processed set so we don't re-process
            processed.add(election_id)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    # Ensure pollster names are harmonized even for previously appended rows.
    harmonize_csv_pollsters()
    print("\nDone!")

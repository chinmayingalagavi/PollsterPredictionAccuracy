#!/usr/bin/env python3
"""
Process exitpoll_accuracy.csv to create exitpoll_accuracy_harmonized.csv.

Steps:
1. Harmonize pollster names
2. Expand single-value predictions to ranges based on average width
3. Calculate accuracy scores (intervalscore, winner_correct, abserror)
"""

import csv
import json
from pathlib import Path

# Interval score parameter - controls penalty for being outside range
ALPHA = 0.5

# Pollster name harmonization mappings
POLLSTER_ALIASES: dict[str, str] = {
    # CVoter
    "ABP News - CVoter": "CVoter",
    "ABP News – C Voter": "CVoter",
    "ABP News – C-Voter": "CVoter",
    "ABP News-C Voter": "CVoter",
    "ABP News-C-Voter": "CVoter",
    "ABP News-CVoter": "CVoter",
    "ABP-CVoter": "CVoter",
    "ABP-C Voter": "CVoter",
    "India Today - CVoter": "CVoter",
    "India Today – CVoter": "CVoter",
    # Axis My India
    "India Today - Axis My India": "Axis My India",
    "India Today -Axis My India": "Axis My India",
    "India Today – Axis My India": "Axis My India",
    "India Today- Axis My India": "Axis My India",
    "India Today-Axis My India": "Axis My India",
    "Aaj Tak - Axis My India": "Axis My India",
    # Matrize
    "News18 Matrize": "Matrize",
    "ABP News-Matrize": "Matrize",
    "India TV -Matrize": "Matrize",
    "Zee News -Matrize": "Matrize",
    "Zee News-Matrize": "Matrize",
    "Republic TV -Matrize": "Matrize",
    "Republic TV-Matrize": "Matrize",
    "IANS-Matrize": "Matrize",
    # P-Marq
    "P Marq": "P-Marq",
    "P-MARQ": "P-Marq",
    "Politique Marquer": "P-Marq",
    "Republic -P Marq": "P-Marq",
    "Republic P-Marq": "P-Marq",
    "Republic TV -P MARQ": "P-Marq",
    # CNX
    "CNX Exit Poll": "CNX",
    "India TV-CNX": "CNX",
    "India TV - CNX": "CNX",
    "India TV -CNX": "CNX",
    # Today's Chanakya
    "News 24 -Today's Chanakya": "Today's Chanakya",
    "News 24 Today's Chanakya": "Today's Chanakya",
    "News 24-Today's Chanakya": "Today's Chanakya",
    "News24-Today's Chanakya": "Today's Chanakya",
    "News18-Today's Chanakya": "Today's Chanakya",
    # Jan Ki Baat
    "India News-Jan Ki Baat": "Jan Ki Baat",
    "India News -Jan Ki Baat": "Jan Ki Baat",
    "NewsX -Jan Ki Baat": "Jan Ki Baat",
    "Suvarna News -Jan Ki Baat": "Jan Ki Baat",
    # Polstrat
    "Polstrat-NewsX": "Polstrat",
    "NewsX Polstrat": "Polstrat",
    "NewsX – Polstrat": "Polstrat",
    "TV9 Bharatvarsh-Polstrat": "Polstrat",
    "TV9 Bharatvarsh -Polstrat": "Polstrat",
    "TV 9 Bharatvarsh-Polstrat": "Polstrat",
    "TV 9 Marathi-Polstrat": "Polstrat",
    # ETG
    "Times Now-ETG": "ETG",
    "Times Now - ETG": "ETG",
    "Times Now -ETG": "ETG",
    "Times Now – ETG": "ETG",
    # Veto
    "Times Now -Veto": "Veto",
    "Times Now-Veto": "Veto",
    "Times Now – VETO": "Veto",
    # People's Pulse
    "People's Pulse - Codemo": "People's Pulse",
    "Peoples Pulse": "People's Pulse",
    "South First - People's Pulse": "People's Pulse",
    "South First – People's Pulse": "People's Pulse",
    "South First-People's Pulse": "People's Pulse",
    # JVC
    "Times Now - JVC": "JVC",
    "Times Now -JVC": "JVC",
    # People's Insight
    "People Insight": "People's Insight",
    # Vote Vibe
    "CNN-News18 - VoteVibe": "Vote Vibe",
    "CNN News18 - VoteVibe": "Vote Vibe",
    # Today's Chanakya misspellings / variants
    "Todays Chanakya": "Today's Chanakya",
    "Today's Chankya": "Today's Chanakya",
    # CVoter source variants
    "Manorama News - CVoter": "CVoter",
    # Zee variants
    "Zee News-BARC": "Zee News-BARC",
    "Zee News-DesignBoxed": "Zee-DesignBoxed",
    "Zee-Design Boxed": "Zee-DesignBoxed",
    # KK Surveys
    "KK Survey and Strategies": "KK Surveys",
    "KK Surveys and Strategies": "KK Surveys",
}


def harmonize_pollster(name: str) -> str:
    """Return the canonical pollster name for a given variant."""
    if not name:
        return name
    return POLLSTER_ALIASES.get(name.strip(), name.strip())


def is_single_value(prediction: list[int]) -> bool:
    """Check if a prediction is a single value (min == max)."""
    return prediction[0] == prediction[1]


def get_prediction_width(prediction: list[int]) -> int:
    """Get the width of a prediction range."""
    return prediction[1] - prediction[0]


def expand_single_predictions(rows: list[dict]) -> list[dict]:
    """
    Expand single-value predictions to ranges based on average width
    of other pollsters for the same party in the same election.

    Only expand a pollster's predictions if ALL their predictions in that
    election are single values. If they have even one range, leave all
    their predictions as-is.
    """
    # Group rows by election_id
    elections: dict[str, list[dict]] = {}
    for row in rows:
        eid = row["election_id"]
        if eid not in elections:
            elections[eid] = []
        elections[eid].append(row)

    # Process each election
    for _election_id, election_rows in elections.items():
        # Calculate average width per party (excluding single-value predictions)
        party_widths: dict[str, list[int]] = {}

        for row in election_rows:
            predictions = json.loads(row["predictions_json"])
            for party, pred in predictions.items():
                width = get_prediction_width(pred)
                if width > 0:  # Only count ranges, not single values
                    if party not in party_widths:
                        party_widths[party] = []
                    party_widths[party].append(width)

        # Calculate average width per party
        avg_widths: dict[str, float] = {}
        for party, widths in party_widths.items():
            if widths:
                avg_widths[party] = sum(widths) / len(widths)
            else:
                avg_widths[party] = 10  # Default width if no ranges exist

        # Default width for election (average of all party widths)
        if avg_widths:
            default_width = sum(avg_widths.values()) / len(avg_widths)
        else:
            default_width = 10

        # Expand single-value predictions (only for pollsters that should be expanded)
        for row in election_rows:
            predictions = json.loads(row["predictions_json"])
            harmonized = {}

            should_expand = all(is_single_value(pred) for pred in predictions.values())

            for party, pred in predictions.items():
                if should_expand and is_single_value(pred):
                    # Get width to use (party-specific or default)
                    width = avg_widths.get(party, default_width)
                    half_width = int(width / 2)
                    center = pred[0]
                    new_min = max(0, center - half_width)
                    new_max = center + half_width
                    harmonized[party] = [new_min, new_max]
                else:
                    harmonized[party] = pred

            row["predictions_json_harmonized"] = json.dumps(harmonized)

    return rows


def calculate_scores(row: dict) -> dict:
    """
    Calculate accuracy scores for a poll.

    - intervalscore: Winkler interval score, normalized by total seats and party count.
      Lower is better. Penalizes wide ranges and misses outside the range.
    - winner_correct: Did the poll predict the party with most seats correctly?
    - abserror: Average of |midpoint - actual| / total_seats across parties.
      Lower is better. Normalized by legislature size, not party size.
    """
    predictions = json.loads(row["predictions_json_harmonized"])
    actual = json.loads(row["actual_results_json"])
    total_seats = int(row["total_seats"])
    score_parties = list(predictions.keys())
    score_parties.extend(
        party for party, seats in actual.items()
        if party not in predictions and seats >= 1
    )

    # Calculate intervalscore (Winkler interval score)
    # Only score parties that won at least 1 seat
    score_sum = 0
    num_parties = 0

    for party in score_parties:
        actual_seats = actual.get(party, 0)
        if actual_seats >= 1:  # Only parties in W_e (won at least 1 seat)
            l_i, u_i = predictions.get(party, [0, 0])
            width = u_i - l_i

            if l_i <= actual_seats <= u_i:
                # In range: score = width
                score_i = width
            elif actual_seats < l_i:
                # Below range: score = width + (2/alpha) * (l_i - y_i)
                score_i = width + (2 / ALPHA) * (l_i - actual_seats)
            else:
                # Above range: score = width + (2/alpha) * (y_i - u_i)
                score_i = width + (2 / ALPHA) * (actual_seats - u_i)

            score_sum += score_i
            num_parties += 1

    # Normalize: (1 / (T_e * P_e)) * sum(score_i)
    if num_parties > 0:
        intervalscore = score_sum / (total_seats * num_parties)
    else:
        intervalscore = 0

    # Calculate abserror: avg of |midpoint - actual| / total_seats
    total_seats = int(row["total_seats"])
    abserror_sum = 0
    abserror_count = 0

    for party in score_parties:
        actual_seats = actual.get(party, 0)
        pred = predictions.get(party, [0, 0])
        midpoint = (pred[0] + pred[1]) / 2
        normalized_error = abs(midpoint - actual_seats) / total_seats
        abserror_sum += normalized_error
        abserror_count += 1

    abserror = abserror_sum / abserror_count if abserror_count > 0 else 0

    # Calculate winner prediction
    # Predicted winner: party/parties with highest midpoint
    prediction_midpoints = {
        party: (pred[0] + pred[1]) / 2
        for party, pred in predictions.items()
    }
    max_prediction = max(prediction_midpoints.values())
    predicted_winners = [
        party for party in predictions.keys()
        if prediction_midpoints[party] == max_prediction
    ]

    # Actual winner: party/parties with most seats
    max_actual = max(actual.values())
    actual_winners = [
        party for party in actual.keys()
        if actual[party] == max_actual
    ]

    predicted_winner = "/".join(predicted_winners)
    actual_winner = "/".join(actual_winners)
    winner_correct = 1 if set(predicted_winners) & set(actual_winners) else 0

    row["intervalscore"] = round(intervalscore, 4)
    row["winner_correct"] = winner_correct
    row["abserror"] = round(abserror, 4)
    row["predicted_winner"] = predicted_winner
    row["actual_winner"] = actual_winner

    return row


def main():
    input_file = Path("exitpoll_accuracy.csv")
    output_file = Path("exitpoll_accuracy_harmonized.csv")

    # Read input
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Read {len(rows)} rows from {input_file}")

    # Step 1: Harmonize pollster names
    for row in rows:
        row["pollster_harmonized"] = harmonize_pollster(row["pollster"])

    # Step 2: Expand single-value predictions
    rows = expand_single_predictions(rows)

    # Step 3: Calculate scores
    for row in rows:
        calculate_scores(row)

    # Write output
    fieldnames = [
        "election_id",
        "election_name",
        "election_date",
        "state",
        "total_seats",
        "pollster",
        "pollster_harmonized",
        "predictions_json",
        "predictions_json_harmonized",
        "actual_results_json",
        "intervalscore",
        "winner_correct",
        "abserror",
        "predicted_winner",
        "actual_winner",
    ]

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_file}")

    # Print summary stats
    total_winner_correct = sum(row["winner_correct"] for row in rows)
    avg_intervalscore = sum(row["intervalscore"] for row in rows) / len(rows)
    avg_abserror = sum(row["abserror"] for row in rows) / len(rows)
    unique_elections = len(set(row["election_id"] for row in rows))
    unique_pollsters = len(set(row["pollster_harmonized"] for row in rows))

    print(f"\n{'='*60}")
    print("OVERALL PERFORMANCE")
    print(f"{'='*60}")
    print(f"  Total exit polls analyzed: {len(rows)}")
    print(f"  State elections covered: {unique_elections}")
    print(f"  Unique polling agencies: {unique_pollsters}")

    # Aggregate by pollster
    from collections import defaultdict
    pollster_data: dict[str, dict] = defaultdict(lambda: {
        "polls": 0,
        "winner_correct": 0,
        "intervalscore_sum": 0,
        "abserror_sum": 0,
    })
    for row in rows:
        p = row["pollster_harmonized"]
        pollster_data[p]["polls"] += 1
        pollster_data[p]["winner_correct"] += row["winner_correct"]
        pollster_data[p]["intervalscore_sum"] += row["intervalscore"]
        pollster_data[p]["abserror_sum"] += row["abserror"]

    # Filter to pollsters with enough observations for a noisy but useful comparison.
    min_polls = 5
    qualified = {p: d for p, d in pollster_data.items() if d["polls"] >= min_polls}

    # Best by interval score
    print(f"\n{'='*60}")
    print(f"BEST POLLSTERS BY INTERVAL SCORE (min {min_polls} polls)")
    print(f"{'='*60}")
    by_interval = sorted(
        qualified.items(),
        key=lambda x: x[1]["intervalscore_sum"] / x[1]["polls"]
    )
    print(f"{'Rank':<6}{'Pollster':<25}{'Polls':<8}{'Avg Score':<10}")
    print("-" * 49)
    for i, (pollster, data) in enumerate(by_interval[:10], 1):
        avg = data["intervalscore_sum"] / data["polls"]
        print(f"{i:<6}{pollster:<25}{data['polls']:<8}{avg:.3f}")

    # Best by abserror
    print(f"\n{'='*60}")
    print(f"BEST POLLSTERS BY ABSERROR (min {min_polls} polls)")
    print(f"{'='*60}")
    by_abserror = sorted(
        qualified.items(),
        key=lambda x: x[1]["abserror_sum"] / x[1]["polls"]
    )
    print(f"{'Rank':<6}{'Pollster':<25}{'Polls':<8}{'Avg Abserror':<12}")
    print("-" * 51)
    for i, (pollster, data) in enumerate(by_abserror[:10], 1):
        avg = data["abserror_sum"] / data["polls"]
        print(f"{i:<6}{pollster:<25}{data['polls']:<8}{avg:.4f}")

    # Best by winner prediction
    print(f"\n{'='*60}")
    print(f"BEST POLLSTERS BY WINNER PREDICTION (min {min_polls} polls)")
    print(f"{'='*60}")
    by_winner = sorted(
        qualified.items(),
        key=lambda x: x[1]["winner_correct"] / x[1]["polls"],
        reverse=True
    )
    print(f"{'Rank':<6}{'Pollster':<25}{'Polls':<8}{'Winner %':<10}")
    print("-" * 49)
    for i, (pollster, data) in enumerate(by_winner[:10], 1):
        pct = 100 * data["winner_correct"] / data["polls"]
        print(f"{i:<6}{pollster:<25}{data['polls']:<8}{pct:.1f}%")


if __name__ == "__main__":
    main()

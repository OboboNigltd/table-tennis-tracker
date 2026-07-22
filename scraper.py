import csv
import os
import requests
from datetime import datetime

CSV_FILE = "table_tennis_scores.csv"

def fetch_sofascore_table_tennis():
    """
    Fetches live and completed table tennis events from Sofascore's public REST API.
    Includes full-time scores, set-by-set breakdowns, and player details.
    """
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            print(f"Retrieved {len(events)} live/recent table tennis matches from Sofascore.")
            return events
        else:
            print(f"Sofascore endpoint returned status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Connection error fetching Sofascore feed: {e}")
        return []

def parse_sofascore_events(events):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    parsed_matches = []

    for event in events:
        tournament_name = event.get("tournament", {}).get("name", "Table Tennis Event")
        category_name = event.get("tournament", {}).get("category", {}).get("name", "")
        full_event = f"{category_name} - {tournament_name}".strip(" - ")

        home_player = event.get("homeTeam", {}).get("name", "Player 1")
        away_player = event.get("awayTeam", {}).get("name", "Player 2")

        # Overall sets score
        home_score = event.get("homeScore", {}).get("current", 0)
        away_score = event.get("awayScore", {}).get("current", 0)
        full_time_score = f"{home_score}-{away_score}"

        # Individual set breakdown
        home_period = event.get("homeScore", {})
        away_period = event.get("awayScore", {})

        set_1 = f"{home_period.get('period1', '-')}-{away_period.get('period1', '-')}" if 'period1' in home_period else "-"
        set_2 = f"{home_period.get('period2', '-')}-{away_period.get('period2', '-')}" if 'period2' in home_period else "-"
        set_3 = f"{home_period.get('period3', '-')}-{away_period.get('period3', '-')}" if 'period3' in home_period else "-"
        set_4 = f"{home_period.get('period4', '-')}-{away_period.get('period4', '-')}" if 'period4' in home_period else "-"
        set_5 = f"{home_period.get('period5', '-')}-{away_period.get('period5', '-')}" if 'period5' in home_period else "-"

        # Calculate sum of points scored per player
        p1_pts = sum([home_period.get(f'period{i}', 0) for i in range(1, 6) if isinstance(home_period.get(f'period{i}'), int)])
        p2_pts = sum([away_period.get(f'period{i}', 0) for i in range(1, 6) if isinstance(away_period.get(f'period{i}'), int)])

        parsed_matches.append({
            "timestamp": timestamp,
            "event": full_event,
            "player_1": home_player,
            "player_2": away_player,
            "full_time_score": full_time_score,
            "set_1": set_1,
            "set_2": set_2,
            "set_3": set_3,
            "set_4": set_4,
            "set_5": set_5,
            "total_p1_points": p1_pts,
            "total_p2_points": p2_pts
        })

    return parsed_matches

def save_to_csv(matches):
    fieldnames = [
        "timestamp", "event", "player_1", "player_2", 
        "full_time_score", "set_1", "set_2", "set_3", 
        "set_4", "set_5", "total_p1_points", "total_p2_points"
    ]

    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        if matches:
            writer.writerows(matches)
            print(f"Successfully recorded {len(matches)} match rows to {CSV_FILE}.")
        else:
            print("No match rows retrieved on this cycle.")

if __name__ == "__main__":
    raw_events = fetch_sofascore_table_tennis()
    processed_matches = parse_sofascore_events(raw_events)
    save_to_csv(processed_matches)

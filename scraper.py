import csv
import os
from datetime import datetime
import requests

# CSV storage configuration
CSV_FILE = "table_tennis_scores.csv"

def fetch_table_tennis_scores():
    """
    Fetches real-time table tennis fixtures and score data.
    Uses public endpoints with standard browser headers to retrieve match logs.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Endpoint URL for live/daily table tennis events
    url = "https://site.api.espn.com/apis/site/v2/sports/summary" # Generic sports endpoint structure
    
    # Custom User-Agent header to ensure reliable API response
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    matches = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            
            for event in events:
                competition = event.get("competitions", [{}])[0]
                competitors = competition.get("competitors", [])
                
                if len(competitors) >= 2:
                    p1 = competitors[0].get("athlete", {}).get("displayName", "Player 1")
                    p2 = competitors[1].get("athlete", {}).get("displayName", "Player 2")
                    
                    # Extract set scores
                    p1_linescores = competitors[0].get("linescores", [])
                    p2_linescores = competitors[1].get("linescores", [])
                    
                    set_1 = f"{p1_linescores[0].get('value', 0)}-{p2_linescores[0].get('value', 0)}" if len(p1_linescores) > 0 else "-"
                    set_2 = f"{p1_linescores[1].get('value', 0)}-{p2_linescores[1].get('value', 0)}" if len(p1_linescores) > 1 else "-"
                    set_3 = f"{p1_linescores[2].get('value', 0)}-{p2_linescores[2].get('value', 0)}" if len(p1_linescores) > 2 else "-"
                    set_4 = f"{p1_linescores[3].get('value', 0)}-{p2_linescores[3].get('value', 0)}" if len(p1_linescores) > 3 else "-"
                    set_5 = f"{p1_linescores[4].get('value', 0)}-{p2_linescores[4].get('value', 0)}" if len(p1_linescores) > 4 else "-"
                    
                    total_p1 = competitors[0].get("score", 0)
                    total_p2 = competitors[1].get("score", 0)
                    
                    matches.append({
                        "timestamp": timestamp,
                        "event": event.get("name", "Table Tennis Tournament"),
                        "player_1": p1,
                        "player_2": p2,
                        "set_1": set_1,
                        "set_2": set_2,
                        "set_3": set_3,
                        "set_4": set_4,
                        "set_5": set_5,
                        "total_p1_points": total_p1,
                        "total_p2_points": total_p2
                    })
        else:
            print(f"Server returned status code: {response.status_code}")

    except Exception as e:
        print(f"Error fetching score data: {e}")

    return matches


def save_to_csv(matches):
    """
    Appends extracted matches to the CSV file.
    Creates header automatically if the file does not exist yet.
    """
    fieldnames = [
        "timestamp", "event", "player_1", "player_2", 
        "set_1", "set_2", "set_3", "set_4", "set_5", 
        "total_p1_points", "total_p2_points"
    ]
    
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        if matches:
            writer.writerows(matches)
            print(f"Successfully recorded {len(matches)} match entry/entries.")
        else:
            print("No new match data recorded on this cycle.")


if __name__ == "__main__":
    score_data = fetch_table_tennis_scores()
    save_to_csv(score_data)

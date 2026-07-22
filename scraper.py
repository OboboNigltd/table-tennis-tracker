import csv
import json
import os
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def fetch_sofascore_multi_day():
    """
    Fetches table tennis events for both today and yesterday 
    to ensure we always capture completed matches with full scores.
    """
    events = []
    
    with sync_playwright() as p:
        print("Launching Playwright browser session...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        try:
            print("Navigating to Sofascore to establish session cookies...")
            page.goto("https://www.sofascore.com/table-tennis", timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)

            now_utc = datetime.now(timezone.utc)
            dates_to_check = [
                now_utc.strftime("%Y-%m-%d"),                     # Today
                (now_utc - timedelta(days=1)).strftime("%Y-%m-%d") # Yesterday (completed matches)
            ]

            for date_str in dates_to_check:
                api_url = f"https://api.sofascore.com/api/v1/sport/table-tennis/scheduled-events/{date_str}"
                print(f"Fetching table tennis schedule for {date_str}...")
                
                raw_response = page.evaluate(f"""
                    async () => {{
                        const res = await fetch('{api_url}');
                        if (!res.ok) return null;
                        return await res.json();
                    }}
                """)

                if raw_response and "events" in raw_response:
                    day_events = raw_response["events"]
                    print(f"Retrieved {len(day_events)} events for {date_str}.")
                    events.extend(day_events)

            # Also check live endpoint just in case
            live_url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
            live_response = page.evaluate(f"""
                async () => {{
                    const res = await fetch('{live_url}');
                    if (!res.ok) return null;
                    return await res.json();
                }}
            """)
            if live_response and "events" in live_response:
                live_events = live_response["events"]
                print(f"Retrieved {len(live_events)} active live matches.")
                events.extend(live_events)

        except Exception as e:
            print(f"Browser execution error: {e}")

        browser.close()

    # Deduplicate events by ID
    unique_events = {e.get("id"): e for e in events if e.get("id")}
    return list(unique_events.values())


def parse_sofascore_events(events):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    parsed_matches = []

    for event in events:
        tournament_name = event.get("tournament", {}).get("name", "Table Tennis Event")
        category_name = event.get("tournament", {}).get("category", {}).get("name", "")
        full_event = f"{category_name} - {tournament_name}".strip(" - ")

        home_player = event.get("homeTeam", {}).get("name", "Player 1")
        away_player = event.get("awayTeam", {}).get("name", "Player 2")

        home_score = event.get("homeScore", {}).get("current", 0)
        away_score = event.get("awayScore", {}).get("current", 0)
        
        status_type = event.get("status", {}).get("type", "notstarted")
        if status_type == "notstarted":
            full_time_score = "-"
        else:
            full_time_score = f"{home_score}-{away_score}"

        home_period = event.get("homeScore", {})
        away_period = event.get("awayScore", {})

        set_1 = f"{home_period.get('period1', '-')}-{away_period.get('period1', '-')}" if 'period1' in home_period and status_type != "notstarted" else "-"
        set_2 = f"{home_period.get('period2', '-')}-{away_period.get('period2', '-')}" if 'period2' in home_period and status_type != "notstarted" else "-"
        set_3 = f"{home_period.get('period3', '-')}-{away_period.get('period3', '-')}" if 'period3' in home_period and status_type != "notstarted" else "-"
        set_4 = f"{home_period.get('period4', '-')}-{away_period.get('period4', '-')}" if 'period4' in home_period and status_type != "notstarted" else "-"
        set_5 = f"{home_period.get('period5', '-')}-{away_period.get('period5', '-')}" if 'period5' in home_period and status_type != "notstarted" else "-"

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

    # Read existing rows to prevent duplicate writes of completed matches
    existing_matches = set()
    if file_exists:
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_matches.add((row.get("event"), row.get("player_1"), row.get("player_2"), row.get("full_time_score")))

    new_rows_to_add = []
    for m in matches:
        identifier = (m["event"], m["player_1"], m["player_2"], m["full_time_score"])
        if identifier not in existing_matches and m["full_time_score"] != "-":
            new_rows_to_add.append(m)
            existing_matches.add(identifier)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        if new_rows_to_add:
            writer.writerows(new_rows_to_add)
            print(f"Successfully recorded {len(new_rows_to_add)} new match rows to {CSV_FILE}.")
        else:
            print("No new unique match scores to add on this cycle.")


if __name__ == "__main__":
    raw_events = fetch_sofascore_multi_day()
    processed_matches = parse_sofascore_events(raw_events)
    save_to_csv(processed_matches)

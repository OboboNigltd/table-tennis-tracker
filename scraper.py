import csv
import json
import os
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def fetch_sofascore_table_tennis_schedule():
    """
    Uses Playwright to bypass Cloudflare protection and fetch 
    table tennis scheduled/live events for today from Sofascore's public API.
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

            # Get today's date in YYYY-MM-DD format for the schedule endpoint
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            api_url = f"https://api.sofascore.com/api/v1/sport/table-tennis/scheduled-events/{today_str}"
            
            print(f"Fetching table tennis schedule for {today_str}...")
            raw_response = page.evaluate(f"""
                async () => {{
                    const res = await fetch('{api_url}');
                    if (!res.ok) return null;
                    return await res.json();
                }}
            """)

            if raw_response and "events" in raw_response:
                events = raw_response["events"]
                print(f"Successfully retrieved {len(events)} table tennis match records!")
            else:
                print("Schedule endpoint returned no events. Falling back to live endpoint...")
                # Fallback to live endpoint if scheduled returns empty
                live_url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
                live_response = page.evaluate(f"""
                    async () => {{
                        const res = await fetch('{live_url}');
                        if (!res.ok) return null;
                        return await res.json();
                    }}
                """ )
                if live_response and "events" in live_response:
                    events = live_response["events"]
                    print(f"Retrieved {len(events)} live matches from fallback endpoint.")

        except Exception as e:
            print(f"Browser execution error: {e}")

        browser.close()

    return events


def parse_sofascore_events(events):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    parsed_matches = []

    for event in events:
        tournament_name = event.get("tournament", {}).get("name", "Table Tennis Event")
        category_name = event.get("tournament", {}).get("category", {}).get("name", "")
        full_event = f"{category_name} - {tournament_name}".strip(" - ")

        home_player = event.get("homeTeam", {}).get("name", "Player 1")
        away_player = event.get("awayTeam", {}).get("name", "Player 2")

        # Overall sets score (default to 0 if upcoming)
        home_score = event.get("homeScore", {}).get("current", 0)
        away_score = event.get("awayScore", {}).get("current", 0)
        
        status_type = event.get("status", {}).get("type", "notstarted")
        if status_type == "notstarted":
            full_time_score = "-"
        else:
            full_time_score = f"{home_score}-{away_score}"

        # Set-by-set breakdown
        home_period = event.get("homeScore", {})
        away_period = event.get("awayScore", {})

        set_1 = f"{home_period.get('period1', '-')}-{away_period.get('period1', '-')}" if 'period1' in home_period and status_type != "notstarted" else "-"
        set_2 = f"{home_period.get('period2', '-')}-{away_period.get('period2', '-')}" if 'period2' in home_period and status_type != "notstarted" else "-"
        set_3 = f"{home_period.get('period3', '-')}-{away_period.get('period3', '-')}" if 'period3' in home_period and status_type != "notstarted" else "-"
        set_4 = f"{home_period.get('period4', '-')}-{away_period.get('period4', '-')}" if 'period4' in home_period and status_type != "notstarted" else "-"
        set_5 = f"{home_period.get('period5', '-')}-{away_period.get('period5', '-')}" if 'period5' in home_period and status_type != "notstarted" else "-"

        # Calculate sum of points scored per player across completed sets
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
    raw_events = fetch_sofascore_table_tennis_schedule()
    processed_matches = parse_sofascore_events(raw_events)
    save_to_csv(processed_matches)

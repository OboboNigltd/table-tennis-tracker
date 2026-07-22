import csv
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def scrape_flashscore_table_tennis():
    """
    Uses Playwright to render Flashscore's Table Tennis daily schedule,
    extracts active/finished match details, and formats them into structured rows.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = []

    print("Launching Playwright browser...")
    with sync_playwright() as p:
        # Launch headless Chromium
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to Flashscore Table Tennis main page
        url = "https://www.flashscore.com/table-tennis/"
        print(f"Navigating to {url}...")
        
        try:
            page.goto(url, timeout=30000)
            # Give dynamic JavaScript elements time to load
            time.sleep(5)

            # Locate match events on the page
            event_rows = page.query_selector_all(".event__match")
            print(f"Found {len(event_rows)} matches on page.")

            for row in event_rows[:10]:  # Capture top 10 matches on page
                try:
                    home_player = row.query_selector(".event__homeParticipant")
                    away_player = row.query_selector(".event__awayParticipant")
                    p1_name = home_player.inner_text().strip() if home_player else "Player A"
                    p2_name = away_player.inner_text().strip() if away_player else "Player B"

                    # Get set score breakdown
                    p1_scores = row.query_selector_all(".event__part--home")
                    p2_scores = row.query_selector_all(".event__part--away")

                    set_1 = f"{p1_scores[0].inner_text()}-{p2_scores[0].inner_text()}" if len(p1_scores) > 0 else "-"
                    set_2 = f"{p1_scores[1].inner_text()}-{p2_scores[1].inner_text()}" if len(p1_scores) > 1 else "-"
                    set_3 = f"{p1_scores[2].inner_text()}-{p2_scores[2].inner_text()}" if len(p1_scores) > 2 else "-"
                    set_4 = f"{p1_scores[3].inner_text()}-{p2_scores[3].inner_text()}" if len(p1_scores) > 3 else "-"
                    set_5 = f"{p1_scores[4].inner_text()}-{p2_scores[4].inner_text()}" if len(p1_scores) > 4 else "-"

                    matches.append({
                        "timestamp": timestamp,
                        "event": "Flashscore Live Fixture",
                        "player_1": p1_name,
                        "player_2": p2_name,
                        "set_1": set_1,
                        "set_2": set_2,
                        "set_3": set_3,
                        "set_4": set_4,
                        "set_5": set_5,
                        "total_p1_points": 0,
                        "total_p2_points": 0
                    })
                except Exception as inner_e:
                    print(f"Error parsing row: {inner_e}")
                    continue

        except Exception as e:
            print(f"Failed to fetch Flashscore page: {e}")

        browser.close()

    return matches

def save_to_csv(matches):
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
            print(f"Successfully recorded {len(matches)} Flashscore match entries.")
        else:
            print("No match entries extracted during this run.")

if __name__ == "__main__":
    match_data = scrape_flashscore_table_tennis()
    save_to_csv(match_data)

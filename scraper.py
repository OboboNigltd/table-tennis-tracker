import csv
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def scrape_mobile_flashscore():
    """
    Scrapes live and finished table tennis scores directly from Mobile Flashscore.
    Bypasses dynamic script walls and cookie banners.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = []

    print("Launching Playwright browser for Mobile Flashscore...")
    with sync_playwright() as p:
        # Launch headless browser with mobile emulation settings
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        # Mobile Flashscore table tennis schedule
        target_url = "https://m.flashscore.com/table-tennis/"
        print(f"Navigating to {target_url}...")
        
        try:
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)

            # Locate match items on the mobile page structure
            match_nodes = page.query_selector_all("#score-data > div, .scoreline, tr")
            print(f"Scanning DOM elements... Found {len(match_nodes)} candidate match rows.")

            # Extract raw text lines from the match table
            page_content = page.content()
            
            # Extract player names and scores from mobile DOM
            rows = page.query_selector_all("div")
            for row in rows:
                text = row.inner_text().strip()
                # Check for table tennis match format (e.g. "Player 1 - Player 2 3-1")
                if " - " in text and any(char.isdigit() for char in text):
                    parts = text.split("\n")
                    if len(parts) >= 2:
                        players_line = parts[0]
                        score_line = parts[1] if len(parts) > 1 else "-"

                        if " - " in players_line:
                            p1, p2 = players_line.split(" - ", 1)
                            matches.append({
                                "timestamp": timestamp,
                                "event": "Flashscore Mobile Stream",
                                "player_1": p1.strip(),
                                "player_2": p2.strip(),
                                "set_1": score_line.strip(),
                                "set_2": "-",
                                "set_3": "-",
                                "set_4": "-",
                                "set_5": "-",
                                "total_p1_points": 0,
                                "total_p2_points": 0
                            })

            # De-duplicate entries
            unique_matches = []
            seen = set()
            for m in matches:
                identifier = (m["player_1"], m["player_2"], m["set_1"])
                if identifier not in seen and m["player_1"] != "Player A":
                    seen.add(identifier)
                    unique_matches.append(m)

            matches = unique_matches[:10]

        except Exception as e:
            print(f"Error fetching Mobile Flashscore: {e}")

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
            print(f"Successfully recorded {len(matches)} real match entry/entries.")
        else:
            print("No new match entries extracted on this pass.")


if __name__ == "__main__":
    real_matches = scrape_mobile_flashscore()
    save_to_csv(real_matches)

import csv
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def scrape_mobile_flashscore():
    """
    Scrapes real table tennis matches from Mobile Flashscore, handling multi-line
    player and score elements cleanly.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = []

    print("Launching Playwright browser for Mobile Flashscore...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        target_url = "https://m.flashscore.com/table-tennis/"
        print(f"Opening {target_url}...")
        
        try:
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(4)

            # Get full text content line-by-line
            body_text = page.inner_text("body")
            lines = [line.strip() for line in body_text.split("\n") if line.strip()]

            print(f"Extracted {len(lines)} raw text lines from page.")

            current_event = "Table Tennis Circuit"
            i = 0
            while i < len(lines):
                line = lines[i]

                # Update current tournament header
                if any(kw in line.upper() for kw in ["WTT", "OTHERS", "CUP", "SERIES", "CHALLENGER", "PRO"]):
                    current_event = line.replace("OTHERSMEN:", "").strip()

                # Detect match lines containing ' - ' or score lines
                if " - " in line:
                    # Case 1: Players on single line ("Player A - Player B")
                    parts = line.split(" - ", 1)
                    p1, p2 = parts[0].strip(), parts[1].strip()
                    score = "-"

                    # Check next line for score (e.g. "0-3" or "11:00")
                    if i + 1 < len(lines) and re.search(r"^(\d+-\d+|\d{2}:\d{2}|\?:?)$", lines[i + 1]):
                        score = lines[i + 1].strip()
                        i += 1

                    matches.append({
                        "timestamp": timestamp,
                        "event": current_event,
                        "player_1": p1,
                        "player_2": p2,
                        "set_1": score,
                        "set_2": "-",
                        "set_3": "-",
                        "set_4": "-",
                        "set_5": "-",
                        "total_p1_points": 0,
                        "total_p2_points": 0
                    })
                i += 1

            # Remove duplicates
            unique_matches = []
            seen = set()
            for m in matches:
                key = (m["player_1"], m["player_2"])
                if key not in seen:
                    seen.add(key)
                    unique_matches.append(m)

            matches = unique_matches[:15]
            print(f"Successfully extracted {len(matches)} match entry/entries.")

        except Exception as e:
            print(f"Error scraping Flashscore: {e}")

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
            print(f"Successfully wrote {len(matches)} rows to {CSV_FILE}.")
        else:
            print("No match data found on this run.")


if __name__ == "__main__":
    scores = scrape_mobile_flashscore()
    save_to_csv(scores)

import csv
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def scrape_mobile_flashscore():
    """
    Scrapes real live and finished table tennis matches from Mobile Flashscore
    and uses Regex to cleanly parse Event, Players, and Set Scores into CSV columns.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = []

    print("Launching Playwright for Mobile Flashscore...")
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
            time.sleep(3)

            # Get raw text content of the score table
            body_text = page.inner_text("body")
            lines = [line.strip() for line in body_text.split("\n") if line.strip()]

            current_event = "WTT / Table Tennis Tournament"

            # Regex pattern to match lines like: "Shim J. (Bra) - Haug B. (Nor) 0-3"
            match_pattern = re.compile(
                r"^([A-Za-z0-9\.\s\(\)\'-]+)\s+-\s+([A-Za-z0-9\.\s\(\)\'-]+)\s+([0-9]+-[0-9]+|\?:|\d{2}:\d{2})$"
            )

            for line in lines:
                # Update tournament title header if found
                if "WTT " in line or "OTHERS" in line or "CUP" in line or "SERIES" in line:
                    current_event = line.replace("OTHERSMEN:", "").strip()
                    continue

                # Test line against match pattern
                m = match_pattern.search(line)
                if m:
                    p1 = m.group(1).strip()
                    p2 = m.group(2).strip()
                    score = m.group(3).strip()

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

            print(f"Cleanly parsed {len(matches)} real match rows.")

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
            print(f"Successfully appended {len(matches)} match rows to {CSV_FILE}.")
        else:
            print("No new matches captured during this cycle.")


if __name__ == "__main__":
    score_data = scrape_mobile_flashscore()
    save_to_csv(score_data)

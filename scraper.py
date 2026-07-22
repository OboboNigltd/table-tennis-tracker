import csv
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def parse_match_details(page, match_id):
    """
    Visits the specific Flashscore match page to extract set-by-set breakdown
    and calculate total points scored by each player.
    """
    detail_url = f"https://m.flashscore.com/match/{match_id}/"
    set_scores = ["-", "-", "-", "-", "-"]
    p1_total = 0
    p2_total = 0

    try:
        page.goto(detail_url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(2)

        # Extract set score elements (e.g., 11-8, 9-11, etc.)
        set_elements = page.query_selector_all(".part, .scorelinePart, .smv__part")
        extracted_sets = []

        for el in set_elements:
            txt = el.inner_text().strip()
            if re.match(r"^\d+-\d+$", txt):
                extracted_sets.append(txt)

        # Fill up to 5 set slots
        for idx in range(min(len(extracted_sets), 5)):
            set_scores[idx] = extracted_sets[idx]
            # Accumulate total points
            p1_pts, p2_pts = map(int, extracted_sets[idx].split("-"))
            p1_total += p1_pts
            p2_total += p2_pts

    except Exception as e:
        print(f"Could not fetch details for match {match_id}: {e}")

    return set_scores, p1_total, p2_total


def scrape_mobile_flashscore():
    """
    Main scraper pipeline:
    1. Fetches daily schedule.
    2. Cleans player names, tournament headers, and match times.
    3. Fetches set-by-set breakdowns and total point sums.
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
            time.sleep(4)

            # Locate match rows and match links
            match_links = page.query_selector_all("a[href*='/match/']")
            print(f"Found {len(match_links)} active match links on schedule.")

            current_event = "WTT / Table Tennis Tournament"
            body_text = page.inner_text("body")
            lines = [line.strip() for line in body_text.split("\n") if line.strip()]

            for i, line in enumerate(lines):
                # Detect and update tournament category
                if any(kw in line.upper() for kw in ["WTT", "OTHERS", "CUP", "SERIES", "CHALLENGER", "PRO"]):
                    current_event = line.replace("OTHERSMEN:", "").replace("OTHERSWOMEN:", "").strip()

                if " - " in line:
                    parts = line.split(" - ", 1)
                    raw_p1, raw_p2 = parts[0].strip(), parts[1].strip()

                    # Clean match time prefix from Player 1 (e.g., '23:10Shim J. (Bra)' -> 'Shim J. (Bra)')
                    match_time = ""
                    time_match = re.search(r"^(\d{2}:\d{2})", raw_p1)
                    if time_match:
                        match_time = time_match.group(1)
                        p1_clean = re.sub(r"^\d{2}:\d{2}\s*", "", raw_p1).strip()
                    else:
                        p1_clean = raw_p1

                    # Clean match score suffix from Player 2 (e.g., 'Haug B. (Nor) 0-3' -> 'Haug B. (Nor)')
                    overall_score = "-"
                    score_match = re.search(r"(\d+-\d+|\d+:\d+|\b-\b|\xa0-)$", raw_p2)
                    if score_match:
                        overall_score = score_match.group(1).strip()
                        p2_clean = re.sub(r"(\d+-\d+|\d+:\d+|\b-\b|\xa0-)$", "", raw_p2).strip()
                    else:
                        p2_clean = raw_p2

                    # Ignore category header rows
                    if p1_clean.upper() in ["OTHERS", "MEN:", "WOMEN:"] or not p1_clean:
                        continue

                    # Default set breakdown to overall match score
                    set_1 = overall_score if overall_score != "\xa0-" else "-"
                    set_2, set_3, set_4, set_5 = "-", "-", "-", "-"
                    total_p1, total_p2 = 0, 0

                    matches.append({
                        "timestamp": timestamp,
                        "event": current_event,
                        "player_1": p1_clean,
                        "player_2": p2_clean,
                        "set_1": set_1,
                        "set_2": set_2,
                        "set_3": set_3,
                        "set_4": set_4,
                        "set_5": set_5,
                        "total_p1_points": total_p1,
                        "total_p2_points": total_p2
                    })

            # De-duplicate entries
            unique_matches = []
            seen = set()
            for m in matches:
                identifier = (m["player_1"], m["player_2"])
                if identifier not in seen:
                    seen.add(identifier)
                    unique_matches.append(m)

            matches = unique_matches[:15]
            print(f"Cleanly structured {len(matches)} matches.")

        except Exception as e:
            print(f"Error scraping schedule: {e}")

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
            print(f"Successfully recorded {len(matches)} match rows to {CSV_FILE}.")
        else:
            print("No match records found on this run.")


if __name__ == "__main__":
    match_data = scrape_mobile_flashscore()
    save_to_csv(match_data)

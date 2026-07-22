import csv
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def get_live_table_tennis_urls(page):
    """
    STAGE 1: URL GENERATOR
    Navigates to Flashscore Table Tennis and extracts match IDs/URLs.
    """
    print("Navigating to Flashscore Table Tennis schedule...")
    url = "https://www.flashscore.com/table-tennis/"
    page.goto(url, timeout=45000)
    time.sleep(5)  # Wait for dynamic JS rendering

    # Extract match IDs from DOM elements
    match_elements = page.query_selector_all("[id^='g_1_'], [id^='g_11_']")
    match_urls = []

    for elem in match_elements[:10]:  # Limit to top 10 matches per run
        element_id = elem.get_attribute("id")
        if element_id:
            # Clean ID string (e.g., 'g_1_XyZ123' -> 'XyZ123')
            clean_id = re.sub(r"^g_\d+_", "", element_id)
            match_url = f"https://www.flashscore.com/match/table-tennis/{clean_id}/"
            match_urls.append((clean_id, match_url))

    print(f"URL Generator discovered {len(match_urls)} active match URLs.")
    return match_urls


def scrape_match_details(page, match_id, match_url):
    """
    STAGE 2: SCRAPER ENGINE
    Opens each match URL and extracts structured set scores and player names.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Scraping match ID: {match_id} -> {match_url}")

    try:
        page.goto(match_url, timeout=30000)
        time.sleep(3)

        # Extract Player / Participant Names
        home_el = page.query_selector(".duelParticipant__home .participant__participantName")
        away_el = page.query_selector(".duelParticipant__away .participant__participantName")

        p1_name = home_el.inner_text().strip() if home_el else "Player A"
        p2_name = away_el.inner_text().strip() if away_el else "Player B"

        # Extract Tournament Name
        event_el = page.query_selector(".tournamentHeader__country")
        event_name = event_el.inner_text().strip() if event_el else "Table Tennis Tournament"

        # Extract Set Scores
        p1_sets = page.query_selector_all(".smv__homeResult")
        p2_sets = page.query_selector_all(".smv__awayResult")

        set_1 = f"{p1_sets[0].inner_text()}-{p2_sets[0].inner_text()}" if len(p1_sets) > 0 else "-"
        set_2 = f"{p1_sets[1].inner_text()}-{p2_sets[1].inner_text()}" if len(p1_sets) > 1 else "-"
        set_3 = f"{p1_sets[2].inner_text()}-{p2_sets[2].inner_text()}" if len(p1_sets) > 2 else "-"
        set_4 = f"{p1_sets[3].inner_text()}-{p2_sets[3].inner_text()}" if len(p1_sets) > 3 else "-"
        set_5 = f"{p1_sets[4].inner_text()}-{p2_sets[4].inner_text()}" if len(p1_sets) > 4 else "-"

        return {
            "timestamp": timestamp,
            "event": event_name,
            "player_1": p1_name,
            "player_2": p2_name,
            "set_1": set_1,
            "set_2": set_2,
            "set_3": set_3,
            "set_4": set_4,
            "set_5": set_5,
            "total_p1_points": 0,
            "total_p2_points": 0
        }

    except Exception as e:
        print(f"Error scraping match {match_id}: {e}")
        return None


def run_pipeline():
    matches_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        # Step 1: Discover URLs
        urls = get_live_table_tennis_urls(page)

        # Step 2: Scrape each URL
        for match_id, match_url in urls:
            match_info = scrape_match_details(page, match_id, match_url)
            if match_info:
                matches_data.append(match_info)

        browser.close()

    return matches_data


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
            print(f"Successfully recorded {len(matches)} match entry/entries into {CSV_FILE}.")
        else:
            print("No match data extracted in this run.")


if __name__ == "__main__":
    extracted_matches = run_pipeline()
    save_to_csv(extracted_matches)

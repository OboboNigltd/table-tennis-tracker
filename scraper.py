import csv
import json
import os
import time
from datetime import datetime
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

CSV_FILE = "table_tennis_scores.csv"

def extract_matches_with_llm(raw_text):
    """
    Sends rendered text to Gemini API to structure match data,
    full-time scores, set-by-set points, and calculate point totals.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is missing.")
        return []

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Analyze the following raw table tennis page content and extract all matches.
    
    For each match, extract:
    - event: Tournament or league category name
    - player_1: First player name and country code (e.g. 'Shim J. (Bra)')
    - player_2: Second player name and country code (e.g. 'Haug B. (Nor)')
    - full_time_score: Overall match set score (e.g., '3-1', '0-3') or '-' if upcoming
    - set_1: Set 1 points score (e.g., '11-8') or '-'
    - set_2: Set 2 points score (e.g., '9-11') or '-'
    - set_3: Set 3 points score or '-'
    - set_4: Set 4 points score or '-'
    - set_5: Set 5 points score or '-'

    Raw Page Content:
    {raw_text[:15000]}
    """

    response_schema = types.Schema(
        type=types.Type.ARRAY,
        items=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "event": types.Schema(type=types.Type.STRING),
                "player_1": types.Schema(type=types.Type.STRING),
                "player_2": types.Schema(type=types.Type.STRING),
                "full_time_score": types.Schema(type=types.Type.STRING),
                "set_1": types.Schema(type=types.Type.STRING),
                "set_2": types.Schema(type=types.Type.STRING),
                "set_3": types.Schema(type=types.Type.STRING),
                "set_4": types.Schema(type=types.Type.STRING),
                "set_5": types.Schema(type=types.Type.STRING),
            },
            required=["event", "player_1", "player_2", "full_time_score"]
        )
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Parsing Error: {e}")
        return []


def run_pipeline():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    formatted_matches = []

    print(f"[{timestamp}] Starting Playwright browser session...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Target mobile stream page which renders cleanly in Playwright
        target_url = "https://m.flashscore.com/table-tennis/"
        print(f"Navigating to {target_url}...")

        try:
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(5)

            raw_content = page.inner_text("body")
            print("Successfully retrieved page DOM. Sending to Gemini LLM...")

            extracted_data = extract_matches_with_llm(raw_content)
            print(f"Gemini LLM extracted {len(extracted_data)} structured match records.")

            for m in extracted_data:
                # Calculate total points scored per player across sets
                p1_total, p2_total = 0, 0
                for s_key in ["set_1", "set_2", "set_3", "set_4", "set_5"]:
                    s_val = m.get(s_key, "-")
                    if s_val and "-" in s_val and s_val != "-":
                        try:
                            pts1, pts2 = map(int, s_val.split("-"))
                            p1_total += pts1
                            p2_total += pts2
                        except ValueError:
                            pass

                formatted_matches.append({
                    "timestamp": timestamp,
                    "event": m.get("event", "Table Tennis Tournament"),
                    "player_1": m.get("player_1", ""),
                    "player_2": m.get("player_2", ""),
                    "full_time_score": m.get("full_time_score", "-"),
                    "set_1": m.get("set_1", "-"),
                    "set_2": m.get("set_2", "-"),
                    "set_3": m.get("set_3", "-"),
                    "set_4": m.get("set_4", "-"),
                    "set_5": m.get("set_5", "-"),
                    "total_p1_points": p1_total,
                    "total_p2_points": p2_total
                })

        except Exception as e:
            print(f"Browser Execution Error: {e}")

        browser.close()

    return formatted_matches


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
            print(f"Successfully saved {len(matches)} rows to {CSV_FILE}.")
        else:
            print("No match rows extracted during this run.")


if __name__ == "__main__":
    matches = run_pipeline()
    save_to_csv(matches)

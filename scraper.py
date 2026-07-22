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
    Passes raw schedule text to Gemini API using Structured Output
    to enforce clean, standardized JSON extraction.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set.")
        return []

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Analyze the following raw table tennis page content and extract all matches.
    For each match, return:
    - event: Tournament or category name
    - player_1: First player's full name and country code
    - player_2: Second player's full name and country code
    - full_time_score: Overall set score (e.g., '3-1', '0-3') or '-' if not started
    - set_1: Set 1 point score (e.g., '11-8') or '-'
    - set_2: Set 2 point score (e.g., '9-11') or '-'
    - set_3: Set 3 point score or '-'
    - set_4: Set 4 point score or '-'
    - set_5: Set 5 point score or '-'

    Raw Page Text:
    {raw_text[:12000]}
    """

    # Enforce strict JSON Schema output
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
        print(f"LLM extraction error: {e}")
        return []


def run_llm_pipeline():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    formatted_matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = context.new_page()

        target_url = "https://m.flashscore.com/table-tennis/"
        print(f"Fetching page from {target_url}...")
        
        try:
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(4)

            raw_text = page.inner_text("body")
            print("Sending raw content to LLM for parsing...")
            
            raw_matches = extract_matches_with_llm(raw_text)
            print(f"LLM returned {len(raw_matches)} structured match entries.")

            for m in raw_matches:
                # Calculate point sums across sets
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
            print(f"Pipeline error: {e}")

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
            print(f"Successfully recorded {len(matches)} match rows to {CSV_FILE}.")
        else:
            print("No new match entries captured.")


if __name__ == "__main__":
    extracted_data = run_llm_pipeline()
    save_to_csv(extracted_data)

import csv
import json
import os
import requests
from datetime import datetime
from google import genai
from google.genai import types

CSV_FILE = "table_tennis_scores.csv"

def fetch_table_tennis_live_data():
    """
    Fetches live table tennis events directly from Sofascore/Flashscore API endpoints
    which include set-by-set point breakdowns natively.
    """
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Direct API fetch error: {e}")
    return None


def parse_and_format_with_llm(raw_json_data):
    """
    Uses Gemini LLM to interpret the raw sports payload, standardize player names,
    extract set breakdowns (Set 1-5), and calculate total scores.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not raw_json_data:
        return []

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Analyze the following raw sports JSON payload for table tennis matches.
    Extract every match and transform it into a structured list where each object has:
    - event: Category or tournament name
    - player_1: Home player full name and country code (e.g. 'Shim J. (Bra)')
    - player_2: Away player full name and country code (e.g. 'Haug B. (Nor)')
    - full_time_score: Overall sets score (e.g. '3-1', '0-3', '0-0')
    - set_1: Set 1 point breakdown (e.g. '11-8') or '-'
    - set_2: Set 2 point breakdown (e.g. '9-11') or '-'
    - set_3: Set 3 point breakdown or '-'
    - set_4: Set 4 point breakdown or '-'
    - set_5: Set 5 point breakdown or '-'

    Raw Data Payload:
    {json.dumps(raw_json_data)[:15000]}
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


def main():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Starting Table Tennis Scraper...")

    raw_data = fetch_table_tennis_live_data()
    if not raw_data:
        print("No live data returned from feed.")
        return

    extracted_matches = parse_and_format_with_llm(raw_data)
    print(f"LLM successfully parsed {len(extracted_matches)} match records.")

    formatted_rows = []
    for m in extracted_matches:
        p1_total, p2_total = 0, 0
        for s_key in ["set_1", "set_2", "set_3", "set_4", "set_5"]:
            s_val = m.get(s_key, "-")
            if s_val and "-" in s_val and s_val != "-":
                try:
                    p1, p2 = map(int, s_val.split("-"))
                    p1_total += p1
                    p2_total += p2
                except ValueError:
                    pass

        formatted_rows.append({
            "timestamp": timestamp,
            "event": m.get("event", "Table Tennis Event"),
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
        if formatted_rows:
            writer.writerows(formatted_rows)
            print(f"Appended {len(formatted_rows)} rows to {CSV_FILE}.")


if __name__ == "__main__":
    main()

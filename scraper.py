import csv
import os
from datetime import datetime
import requests

# The name of the spreadsheet file where scores will be saved
CSV_FILE = "table_tennis_scores.csv"

def fetch_and_save_scores():
    # Example placeholder structure for match score records
    # (We will adjust the web address/API URL later based on your preferred data source)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Structure of the spreadsheet columns
    fieldnames = [
        "timestamp", "event", "player_1", "player_2", 
        "set_1", "set_2", "set_3", "set_4", "set_5", 
        "total_p1_points", "total_p2_points"
    ]
    
    file_exists = os.path.isfile(CSV_FILE)

    # Open or create the CSV file in append mode
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write column headers if the file is brand new
        if not file_exists:
            writer.writeheader()

if __name__ == "__main__":
    fetch_and_save_scores()
    print("Scraper script executed successfully.")

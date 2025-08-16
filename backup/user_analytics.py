# user_analytics.py (v1.2 - Mutually Exclusive Reporting)
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import argparse

def analyze_user_activity(db_file):
    """
    Connects to the SQLite database, analyzes the interaction logs for all users,
    and prints a detailed, mutually exclusive activity report.
    """
    try:
        con = sqlite3.connect(db_file)
        cur = con.cursor()
        res = cur.execute("SELECT profile_hash, profile_json FROM user")
        all_users = res.fetchall()
        con.close()
    except sqlite3.Error as e:
        print(f"--- DATABASE ERROR ---")
        print(f"Could not connect to or read from '{db_file}'.")
        print(f"Error details: {e}")
        print("Please ensure the file exists and is a valid SQLite database.")
        return

    total_registered_users = len(all_users)
    if total_registered_users == 0:
        print("No registered users found in the database.")
        return

    # --- Initialize variables for tracking stats ---
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    three_days_ago = now - timedelta(days=3)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    # Use lists for each MUTUALLY EXCLUSIVE bucket
    bucket_daily = []
    bucket_3_day = []
    bucket_weekly = []
    bucket_monthly = []
    bucket_lapsed = []
    
    monthly_interaction_counts = defaultdict(int)

    # --- Process each user's interaction log ---
    for profile_hash, profile_json_str in all_users:
        try:
            profile = json.loads(profile_json_str)
            interaction_log = profile.get("interaction_log", [])
            
            if not interaction_log:
                bucket_lapsed.append(profile_hash) # User exists but has never interacted
                continue

            most_recent_interaction_ts_str = interaction_log[0].get("timestamp")
            if not most_recent_interaction_ts_str:
                bucket_lapsed.append(profile_hash) # User has logs, but they are malformed
                continue
            
            interaction_dt = datetime.fromisoformat(most_recent_interaction_ts_str).astimezone(timezone.utc)

            # NEW: Use an if/elif/else chain for mutually exclusive categorization
            if interaction_dt >= one_day_ago:
                bucket_daily.append(profile_hash)
            elif interaction_dt >= three_days_ago:
                bucket_3_day.append(profile_hash)
            elif interaction_dt >= one_week_ago:
                bucket_weekly.append(profile_hash)
            elif interaction_dt >= one_month_ago:
                bucket_monthly.append(profile_hash)
            else:
                bucket_lapsed.append(profile_hash)
            
            # This frequency calculation remains the same, as it's a separate metric
            for interaction in interaction_log:
                ts_str = interaction.get("timestamp")
                if not ts_str: continue
                
                log_dt = datetime.fromisoformat(ts_str).astimezone(timezone.utc)
                if log_dt >= one_month_ago:
                    monthly_interaction_counts[profile_hash] += 1
                else:
                    break

        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Could not parse profile for user hash {profile_hash}. Error: {e}")
            continue

    # --- Calculate the frequency metric ---
    users_active_twice_a_month = {
        user_hash for user_hash, count in monthly_interaction_counts.items() if count >= 2
    }
    
    # --- Print the final report with clearer, exclusive labels ---
    print("\n--- Tyra User Activity Report ---")
    print(f"Analyzing database file: '{db_file}'")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 35)

    print(f"1. Total Registered Users: {total_registered_users}")
    print("\n--- User Engagement (Mutually Exclusive) ---")
    print(f"   - Active in last 24 hours:       {len(bucket_daily)}")
    print(f"   - Active 1-3 days ago:           {len(bucket_3_day)}")
    print(f"   - Active 3-7 days ago:           {len(bucket_weekly)}")
    print(f"   - Active 7-30 days ago:          {len(bucket_monthly)}")
    print(f"   - Lapsed (no activity >30 days): {len(bucket_lapsed)}")
    
    # Verification check
    total_categorized = len(bucket_daily) + len(bucket_3_day) + len(bucket_weekly) + len(bucket_monthly) + len(bucket_lapsed)
    print(f"   ---------------------------------------")
    print(f"   Sum of Categories:             {total_categorized} (Should match total users)")
    
    print("\n--- User Frequency (Last 30 Days) ---")
    print(f"   - Users with 2+ sessions:      {len(users_active_twice_a_month)}")

    print("\n--- Report Complete ---")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Analyzes user activity from a Tyra application's SQLite database."
    )
    parser.add_argument(
        "database_file", 
        help="The path to the SQLite database file to be analyzed."
    )
    args = parser.parse_args()
    
    analyze_user_activity(args.database_file)
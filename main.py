import requests
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()


class SteamAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.steampowered.com"

    def get_player_summary(self, steam_id):
        """Get basic player information"""
        url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/"
        params = {"key": self.api_key, "steamids": steam_id}
        response = requests.get(url, params=params)
        return response.json()

    def get_owned_games(self, steam_id):
        """Get list of games owned by the player"""
        url = f"{self.base_url}/IPlayerService/GetOwnedGames/v0001/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "format": "json",
            "include_appinfo": 1,
            "include_played_free_games": 1,
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_player_achievements(self, steam_id, app_id):
        """Get achievement data for a specific game"""
        url = f"{self.base_url}/ISteamUserStats/GetPlayerAchievements/v0001/"
        params = {"key": self.api_key, "steamid": steam_id, "appid": app_id}
        response = requests.get(url, params=params)
        return response.json()


def process_single_game(steam, steam_id, game, game_index, total_games, games_with_achievements, lock):
    """Process a single game - thread-safe function"""
    try:
        game_name = game['name']
        app_id = game['appid']
        
        with lock:
            print(f"Processing game {game_index}/{total_games}: {game_name} (AppID: {app_id})")
        
        # Get achievements for this game
        achievements_data = steam.get_player_achievements(steam_id, app_id)
        
        if achievements_data.get("playerstats", {}).get("success"):
            achievements = achievements_data["playerstats"].get("achievements", [])
            
            if achievements:  # Only save games that have achievements
                game_data = {
                    "appid": app_id,
                    "name": game_name,
                    "playtime_forever": game.get("playtime_forever", 0),
                    "achievements": []
                }
                
                # Check if game has at least one locked achievement (achieved: 0)
                has_locked_achievements = False
                
                for achievement in achievements:
                    achievement_data = {
                        "apiname": achievement["apiname"],  # This is the achievement ID
                        "achieved": achievement["achieved"],
                        "unlocktime": achievement.get("unlocktime", 0),
                        "name": achievement.get("name", ""),
                        "description": achievement.get("description", "")
                    }
                    game_data["achievements"].append(achievement_data)
                    
                    # Check if this achievement is locked (achieved: 0)
                    if achievement["achieved"] == 0:
                        has_locked_achievements = True
                
                # Only save games that have at least one locked achievement
                if has_locked_achievements:
                    with lock:
                        games_with_achievements.append(game_data)
                        locked_count = sum(1 for ach in achievements if ach["achieved"] == 0)
                        print(f"  ✓ Found {len(achievements)} achievements ({locked_count} locked)")
                else:
                    with lock:
                        print(f"  ⏭ Skipping - all {len(achievements)} achievements already unlocked")
            else:
                with lock:
                    print(f"  ❌ No achievements found")
        else:
            with lock:
                print(f"  ❌ Failed to get achievements or game not owned")
                
        # Small delay to respect Steam API rate limits
        time.sleep(0.05)
        
    except Exception as e:
        with lock:
            print(f"  ❌ Error processing {game.get('name', 'Unknown')}: {e}")


def main():
    api_key = os.getenv("STEAM_API_KEY")
    steam_id = os.getenv("STEAM_ID")

    if not api_key or not steam_id:
        print("Please set STEAM_API_KEY and STEAM_ID in your .env file")
        return

    # Clear existing data.json file for fresh start
    print("Clearing existing data.json...")
    if os.path.exists("data.json"):
        os.remove("data.json")
        print("Existing data.json removed")
    
    steam = SteamAPI(api_key)
    games_with_achievements = []
    lock = threading.Lock()  # Thread-safe lock for shared data

    # Get owned games
    print("Getting owned games...")
    games_data = steam.get_owned_games(steam_id)
    if "games" in games_data["response"]:
        games = games_data["response"]["games"]
        print(f"Total games: {len(games)}")
        print("🚀 Starting parallel processing with 8 threads...\n")
        
        try:
            # Use ThreadPoolExecutor for parallel processing
            max_workers = 8  # Number of concurrent threads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all games for processing
                future_to_game = {
                    executor.submit(
                        process_single_game, 
                        steam, steam_id, game, i, len(games), 
                        games_with_achievements, lock
                    ): (game, i) 
                    for i, game in enumerate(games, 1)
                }
                
                # Process completed futures
                completed_count = 0
                for future in as_completed(future_to_game):
                    completed_count += 1
                    
                    # Save progress every 100 games
                    if completed_count % 100 == 0:
                        with lock:
                            print(f"\n--- Progress: {completed_count}/{len(games)} games processed ---")
                            print(f"--- Games with locked achievements so far: {len(games_with_achievements)} ---")
                            
                            # Save progress
                            with open("data.json", "w", encoding="utf-8") as f:
                                json.dump({
                                    "steam_id": steam_id,
                                    "total_games_with_locked_achievements": len(games_with_achievements),
                                    "games": games_with_achievements
                                }, f, indent=2, ensure_ascii=False)
                            print("Progress saved!\n")
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Interrupted! Saving progress for {len(games_with_achievements)} games...")
            # Save what we have so far
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "steam_id": steam_id,
                    "total_games_with_locked_achievements": len(games_with_achievements),
                    "games": games_with_achievements
                }, f, indent=2, ensure_ascii=False)
            print("Progress saved to data.json")
            return
    
    # Save to JSON file
    print(f"\nSaving data for {len(games_with_achievements)} games with locked achievements...")
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({
            "steam_id": steam_id,
            "total_games_with_locked_achievements": len(games_with_achievements),
            "games": games_with_achievements
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Data saved to data.json!")
    print(f"📊 Total games with locked achievements: {len(games_with_achievements)}")
    
    # Calculate total locked achievements
    total_locked = sum(
        len([ach for ach in game["achievements"] if ach["achieved"] == 0]) 
        for game in games_with_achievements
    )
    print(f"🎯 Total locked achievements to unlock: {total_locked}")


if __name__ == "__main__":
    main()
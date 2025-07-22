import requests
import os
import sys
import json
import time
import threading
import struct
import winreg
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Try to load dotenv, but continue if not available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Note: python-dotenv not available, skipping .env file loading")

# Global log file handle
log_file = None


def log_print(message):
    """Print to console and write to log file"""
    print(message)
    if log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        log_file.flush()


def setup_steam_dlls():
    """Verify Steam DLLs are available (no copying needed)"""

    def get_steam_path():
        """Get Steam installation path from registry"""
        try:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
            ]

            for hkey, path in registry_paths:
                try:
                    key = winreg.OpenKey(hkey, path)
                    install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    winreg.CloseKey(key)
                    return install_path
                except (WindowsError, FileNotFoundError):
                    continue

            # Fallback paths
            fallback_paths = [
                r"C:\Program Files (x86)\Steam",
                r"C:\Program Files\Steam",
                r"C:\Steam",
            ]

            for path in fallback_paths:
                if os.path.exists(path):
                    return path

        except Exception as e:
            print(f"❌ Error finding Steam path: {e}")

        return None

    steam_path = get_steam_path()
    if not steam_path:
        print("❌ Steam installation not found!")
        print("Please ensure Steam is installed and try again.")
        return False

    print(f"🔍 Found Steam at: {steam_path}")

    # Check if required DLLs exist in Steam installation
    required_dlls = [
        "vstdlib_s64.dll",
        "tier0_s64.dll",
        "steamclient64.dll",
    ]

    success = True
    for dll_name in required_dlls:
        steam_dll_path = os.path.join(steam_path, dll_name)
        if os.path.exists(steam_dll_path):
            print(f"✅ Found {dll_name}")
        else:
            print(f"❌ Missing {dll_name} at {steam_dll_path}")
            success = False

    if success:
        print(f"✅ All required Steam DLLs found in: {steam_path}")

    return success


class SteamSchemaReader:
    """Reads Steam achievement schema files to detect protected achievements"""

    def __init__(self):
        self.steam_path = self._get_steam_path()
        self.schema_cache = {}  # Cache for loaded schemas

    def _get_steam_path(self):
        """Get Steam installation path from registry"""
        try:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
            ]

            for hkey, path in registry_paths:
                try:
                    key = winreg.OpenKey(hkey, path)
                    install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    winreg.CloseKey(key)
                    return install_path
                except (WindowsError, FileNotFoundError):
                    continue

            # Fallback paths
            fallback_paths = [
                r"C:\Program Files (x86)\Steam",
                r"C:\Program Files\Steam",
            ]
            for path in fallback_paths:
                if os.path.exists(path):
                    return path

            return None
        except Exception:
            return None

    def _read_kv_file(self, file_path):
        """Read Steam KeyValue binary file format"""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # Simple KeyValue parser for achievement schema
            # Steam's KeyValue format is complex, this is a basic implementation
            achievements = {}

            # Look for achievement definitions in the binary data
            # This is a simplified approach - in practice, you'd need a full KV parser
            pos = 0
            while pos < len(data) - 20:
                # Look for achievement ID patterns
                if data[pos : pos + 4] == b"\x01\x00\x00\x00":  # Common pattern
                    try:
                        # Try to extract achievement info
                        # This is a simplified extraction - real implementation would be more complex
                        achievement_id = ""
                        permission = 0

                        # Look for permission field nearby
                        check_range = min(100, len(data) - pos)
                        for i in range(check_range):
                            if pos + i + 4 < len(data):
                                # Check for permission patterns
                                val = struct.unpack("<I", data[pos + i : pos + i + 4])[
                                    0
                                ]
                                if val in [0, 1, 2, 3]:  # Common permission values
                                    permission = val
                                    break

                        if achievement_id:
                            achievements[achievement_id] = {"permission": permission}
                    except:
                        pass

                pos += 1

            return achievements
        except Exception as e:
            print(f"Error reading schema file {file_path}: {e}")
            return {}

    def is_achievement_protected(self, app_id, achievement_id):
        """Check if an achievement is protected based on Steam schema"""
        if not self.steam_path:
            return False  # If can't find Steam, assume not protected

        # Check cache first
        if app_id in self.schema_cache:
            schema = self.schema_cache[app_id]
            if achievement_id in schema:
                permission = schema[achievement_id].get("permission", 0)
                return (permission & 3) != 0  # Protected if bits 0 or 1 are set

        # Load schema file
        schema_file = os.path.join(
            self.steam_path, "appcache", "stats", f"UserGameStatsSchema_{app_id}.bin"
        )

        if not os.path.exists(schema_file):
            # If schema file doesn't exist, assume not protected
            return False

        try:
            schema = self._read_kv_file(schema_file)
            self.schema_cache[app_id] = schema

            if achievement_id in schema:
                permission = schema[achievement_id].get("permission", 0)
                return (permission & 3) != 0  # Protected if bits 0 or 1 are set

            # If achievement not found in schema, assume not protected
            return False

        except Exception as e:
            print(f"Error loading schema for app {app_id}: {e}")
            return False  # If error, assume not protected


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
            "skip_unvetted_apps": 0,
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_player_achievements(self, steam_id, app_id):
        """Get achievement data for a specific game"""
        url = f"{self.base_url}/ISteamUserStats/GetPlayerAchievements/v0001/"
        params = {"key": self.api_key, "steamid": steam_id, "appid": app_id}
        response = requests.get(url, params=params)
        return response.json()


def process_single_game(
    steam,
    steam_id,
    game,
    game_index,
    total_games,
    games_with_achievements,
    lock,
    schema_reader,
    stop_processing,
):
    """Process a single game - thread-safe function"""
    try:
        # Check if we should stop processing
        if stop_processing.is_set():
            return

        game_name = game["name"]
        app_id = game["appid"]

        with lock:
            log_print(
                f"Processing game {game_index}/{total_games}: {game_name} (AppID: {app_id})"
            )

        # Get achievements for this game
        achievements_data = steam.get_player_achievements(steam_id, app_id)

        if achievements_data.get("playerstats", {}).get("success"):
            achievements = achievements_data["playerstats"].get("achievements", [])

            if achievements:  # Only save games that have achievements
                game_data = {
                    "appid": app_id,
                    "name": game_name,
                    "playtime_forever": game.get("playtime_forever", 0),
                    "achievements": [],
                }

                # Check if game has at least one locked achievement (achieved: 0)
                has_locked_achievements = False
                total_locked = 0

                for achievement in achievements:
                    achievement_data = {
                        "apiname": achievement["apiname"],  # This is the achievement ID
                        "achieved": achievement["achieved"],
                        "unlocktime": achievement.get("unlocktime", 0),
                        "name": achievement.get("name", ""),
                        "description": achievement.get("description", ""),
                        "protected": False,
                    }

                    # Check if this achievement is locked (achieved: 0)
                    if achievement["achieved"] == 0:
                        total_locked += 1
                        has_locked_achievements = True

                    game_data["achievements"].append(achievement_data)

                # Only save games that have at least one locked achievement
                if has_locked_achievements:
                    with lock:
                        games_with_achievements.append(game_data)
                        log_print(
                            f"  ✓ Found {len(achievements)} achievements ({total_locked} locked)"
                        )

                else:
                    with lock:
                        log_print(
                            f"  ⏭ Skipping - all {len(achievements)} achievements already unlocked"
                        )
            else:
                with lock:
                    log_print(f"  ❌ No achievements found")
        else:
            with lock:
                log_print(f"  ❌ Failed to get achievements or game not owned")

        # Small delay to respect Steam API rate limits
        time.sleep(0.05)

    except Exception as e:
        with lock:
            log_print(f"  ❌ Error processing {game.get('name', 'Unknown')}: {e}")


def check_steam_running():
    """Check if Steam is running"""
    print("🔍 Checking Steam status...")

    steam_running = False

    # Use tasklist command to check for Steam
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and "steam.exe" in result.stdout.lower():
            steam_running = True
    except Exception as e:
        print(f"Steam check failed: {e}")

    if not steam_running:
        print("❌ Steam is not running!")
        print("\n📋 REQUIRED STEPS:")
        print("1. Start Steam application")
        print("2. Log into your Steam account")
        print("3. Make sure you're connected to the internet")
        print("4. Run this program again")
        try:
            input("\nPress Enter to exit...")
        except:
            pass
        sys.exit(1)

    print("✅ Steam is running")
    return True


def get_steam_credentials():
    """Get or request Steam API credentials"""
    print("=" * 60)
    print("         STEAM ACHIEVEMENT UNLOCKER")
    print("=" * 60)
    print()

    # Check Steam first
    check_steam_running()

    # Check if .env file exists
    api_key = None
    steam_id = None

    if os.path.exists(".env"):
        print("📄 Found existing .env file")
        try:
            with open(".env", "r") as f:
                content = f.read()

            # Parse .env file
            for line in content.split("\n"):
                if line.startswith("STEAM_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                elif line.startswith("STEAM_ID="):
                    steam_id = line.split("=", 1)[1].strip()

            if api_key and steam_id:
                print("✅ Found valid credentials in .env file")
                return api_key, steam_id

        except Exception as e:
            print(f"❌ Error reading .env file: {e}")

    # Request credentials from user
    print("\n🔑 Steam API credentials needed:")
    print("\n📋 HOW TO GET YOUR STEAM API KEY:")
    print("1. Go to: https://steamcommunity.com/dev/apikey")
    print("2. Log in with your Steam account")
    print("3. Copy the generated API key")

    print("\n📋 HOW TO GET YOUR STEAM ID:")
    print("1. Go to: https://steamid.io/")
    print("2. Enter your Steam profile URL or username")
    print("3. Copy the SteamID64 number")

    print("\n" + "=" * 50)

    # Get API key
    while not api_key:
        api_key_input = input("\nEnter your Steam API key: ").strip()
        if len(api_key_input) == 32 and all(
            c in "0123456789ABCDEF" for c in api_key_input.upper()
        ):
            api_key = api_key_input
            print("✅ Valid API key format")
        else:
            print("❌ Invalid API key format (should be 32 hex characters)")

    # Get Steam ID
    while not steam_id:
        steam_id_input = input("Enter your Steam ID (17-digit number): ").strip()
        if steam_id_input.isdigit() and len(steam_id_input) == 17:
            steam_id = steam_id_input
            print("✅ Valid Steam ID format")
        else:
            print("❌ Invalid Steam ID format (should be 17 digits)")

    # Save to .env file
    try:
        with open(".env", "w") as f:
            f.write(f"STEAM_API_KEY={api_key}\n")
            f.write(f"STEAM_ID={steam_id}\n")
        print(f"✅ Credentials saved to .env file")
        return api_key, steam_id

    except Exception as e:
        print(f"❌ Error saving credentials: {e}")
        return api_key, steam_id


def main():
    global log_file

    # Get credentials first
    api_key, steam_id = get_steam_credentials()

    # Initialize log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"steam_achievement_log_{timestamp}.txt"
    log_file = open(log_filename, "w", encoding="utf-8")
    log_print(f"Starting Steam Achievement Unlocker - Log file: {log_filename}")

    # Set environment variables for this session
    os.environ["STEAM_API_KEY"] = api_key
    os.environ["STEAM_ID"] = steam_id

    # Clear existing data.json file for fresh start
    log_print("Clearing existing data.json...")
    if os.path.exists("data.json"):
        os.remove("data.json")
        log_print("Existing data.json removed")

    steam = SteamAPI(api_key)
    games_with_achievements = []
    lock = threading.Lock()  # Thread-safe lock for shared data
    stop_processing = threading.Event()  # Signal to stop processing

    # Get owned games
    log_print("Getting owned games...")
    games_data = steam.get_owned_games(steam_id)
    if "games" in games_data["response"]:
        games = games_data["response"]["games"]
        log_print(f"Total games: {len(games)}")
        log_print("🚀 Starting parallel processing with 8 threads...")
        log_print("📊 Progress will be shown every 10 games processed")
        log_print("⏱️ This may take a few minutes depending on your library size...\n")

        try:
            # Use ThreadPoolExecutor for parallel processing
            max_workers = 32  # Number of concurrent threads

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Initialize schema reader
                schema_reader = SteamSchemaReader()

                # Submit all games for processing
                future_to_game = {
                    executor.submit(
                        process_single_game,
                        steam,
                        steam_id,
                        game,
                        i,
                        len(games),
                        games_with_achievements,
                        lock,
                        schema_reader,
                        stop_processing,
                    ): (game, i)
                    for i, game in enumerate(games, 1)
                }

                # Process completed futures
                completed_count = 0
                last_percentage = -1

                for future in as_completed(future_to_game):
                    completed_count += 1

                    # Check if we should stop early
                    if stop_processing.is_set():
                        log_print(f"\n🛑 Stopping process as requested")
                        break

                    # Show progress every 5%
                    current_percentage = int((completed_count / len(games)) * 100)
                    if (
                        current_percentage != last_percentage
                        and current_percentage % 5 == 0
                    ):
                        progress_bar = (
                            "=" * (current_percentage // 2)
                            + ">"
                            + " " * (50 - current_percentage // 2)
                        )
                        with lock:
                            log_print(
                                f"\rProgress: [{progress_bar}] {current_percentage}% ({completed_count}/{len(games)}) - Found {len(games_with_achievements)} games with locked achievements"
                            )
                        last_percentage = current_percentage

                    # Show simple progress every 10 games for smaller libraries
                    elif completed_count % 10 == 0 or completed_count == len(games):
                        progress_bar = "=" * int((completed_count / len(games)) * 50)
                        remaining_bar = " " * (50 - len(progress_bar))
                        percentage = int((completed_count / len(games)) * 100)
                        with lock:
                            log_print(
                                f"Progress: [{progress_bar}{remaining_bar}] {percentage}% ({completed_count}/{len(games)}) - Found {len(games_with_achievements)} games with locked achievements"
                            )

                    # Save progress every 100 games
                    if completed_count % 100 == 0:
                        with lock:
                            log_print(
                                f"\n--- Checkpoint: {completed_count}/{len(games)} games processed ---"
                            )

                            # Save progress
                            with open("data.json", "w", encoding="utf-8") as f:
                                json.dump(
                                    {
                                        "steam_id": steam_id,
                                        "total_games_with_locked_achievements": len(
                                            games_with_achievements
                                        ),
                                        "games": games_with_achievements,
                                    },
                                    f,
                                    indent=2,
                                    ensure_ascii=False,
                                )
                            log_print("Progress checkpoint saved!\n")

        except KeyboardInterrupt:
            log_print(
                f"\n\n⚠️ Interrupted! Saving progress for {len(games_with_achievements)} games with locked achievements..."
            )
            # Save what we have so far
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "steam_id": steam_id,
                        "total_games_with_locked_achievements": len(
                            games_with_achievements
                        ),
                        "games": games_with_achievements,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            log_print("Progress saved to data.json")
            if log_file:
                log_file.close()
            return

    # Save to JSON file
    log_print(
        f"\nSaving data for {len(games_with_achievements)} games with locked achievements..."
    )
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "steam_id": steam_id,
                "total_games_with_locked_achievements": len(games_with_achievements),
                "games": games_with_achievements,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    log_print(f"✅ Data saved to data.json!")
    log_print(
        f"📊 Total games with locked achievements: {len(games_with_achievements)}"
    )

    # Calculate total locked achievements
    total_locked = sum(
        len([ach for ach in game["achievements"] if ach["achieved"] == 0])
        for game in games_with_achievements
    )
    log_print(f"🎯 Total locked achievements to unlock: {total_locked}")

    # Close log file
    if log_file:
        log_file.close()

    # Now run the achievement unlocker
    print("\n" + "=" * 60)
    print("🏆 STARTING ACHIEVEMENT UNLOCKING PROCESS")
    print("=" * 60)
    print("⚠️  WARNING: This will unlock achievements in all games!")

    confirm = (
        input("\nDo you want to proceed with unlocking achievements? (y/n): ")
        .strip()
        .lower()
    )
    if confirm == "y":
        try:
            # DEBUG: Print environment info
            print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
            print(f"🔍 DEBUG: Python path: {sys.path[0] if sys.path else 'Unknown'}")
            print(f"🔍 DEBUG: Data.json exists: {os.path.exists('data.json')}")
            print(f"🔍 DEBUG: Steam DLL exists: {os.path.exists('DLLs')}")

            # Verify Steam DLLs are available
            print("🔧 Verifying Steam DLLs...")
            if not setup_steam_dlls():
                print(
                    "❌ Failed to find required Steam DLLs. Please ensure Steam is installed."
                )
                return

            print(
                f"🔍 DEBUG: Steam DLL exists after extraction: {os.path.exists('DLLs')}"
            )

            # Import and run the working steam_client_achievements
            print("Loading steam achievement unlocker...")
            import steam_client_achievements

            # Call the working process_all_games function
            print("Starting achievement unlocking process...")
            steam_client_achievements.process_all_games()

        except ImportError:
            print("❌ Error: steam_client_achievements module not found")
        except Exception as e:
            print(f"❌ Error running achievement unlocker: {e}")
            import traceback

            print(f"Full traceback:\n{traceback.format_exc()}")
    else:
        print("❌ Achievement unlocking cancelled by user")
        print("Your data.json file has been saved for future use.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback

        print(f"Full traceback:\n{traceback.format_exc()}")
        try:
            input("\nPress Enter to exit...")
        except:
            import time

            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n❌ Program interrupted by user")
        try:
            input("Press Enter to exit...")
        except:
            pass

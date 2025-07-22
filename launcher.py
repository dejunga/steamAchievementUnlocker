#!/usr/bin/env python3
"""
Steam Achievement Unlocker Launcher
Comprehensive setup and execution tool for Steam achievement unlocking
"""

import os
import sys
import json
import time
import subprocess
import winreg
from pathlib import Path
from datetime import datetime

# Try to import optional dependencies
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, using alternative Steam detection")

# Try to import dotenv, if not available use alternative method
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not available, using alternative method")

    # Create a dummy load_dotenv function
    def load_dotenv():
        pass


class SteamLauncher:
    def __init__(self):
        self.steam_path = None
        self.steam_api_key = None
        self.steam_id = None
        self.env_file = ".env"

    def print_header(self):
        """Print application header"""
        print("=" * 60)
        print("         STEAM ACHIEVEMENT UNLOCKER LAUNCHER")
        print("=" * 60)
        print()

    def check_steam_running(self):
        """Check if Steam is running and user is logged in"""
        print("🔍 Checking Steam status...")

        steam_running = False

        if PSUTIL_AVAILABLE:
            # Use psutil if available
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if proc.info["name"].lower() == "steam.exe":
                            steam_running = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as e:
                print(f"psutil check failed: {e}, trying alternative method...")
                steam_running = False

        if not steam_running:
            # Alternative method using tasklist command
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and "steam.exe" in result.stdout.lower():
                    steam_running = True
            except Exception as e:
                print(f"Alternative Steam check failed: {e}")

        if not steam_running:
            print("❌ Steam is not running!")
            print("\n📋 REQUIRED STEPS:")
            print("1. Start Steam application")
            print("2. Log into your Steam account")
            print("3. Make sure you're connected to the internet")
            print("4. Run this launcher again")
            input("\nPress Enter to exit...")
            return False

        print("✅ Steam is running")
        return True

    def find_steam_path(self):
        """Find Steam installation path"""
        print("🔍 Finding Steam installation...")

        try:
            # Try registry locations
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
                    if os.path.exists(install_path):
                        self.steam_path = install_path
                        print(f"✅ Found Steam at: {install_path}")
                        return True
                except (WindowsError, FileNotFoundError):
                    continue

            # Fallback paths
            fallback_paths = [
                r"C:\Program Files (x86)\Steam",
                r"C:\Program Files\Steam",
            ]

            for path in fallback_paths:
                if os.path.exists(path):
                    self.steam_path = path
                    print(f"✅ Found Steam at: {path}")
                    return True

            print("❌ Could not find Steam installation")
            return False

        except Exception as e:
            print(f"❌ Error finding Steam: {e}")
            return False

    def get_steam_credentials(self):
        """Get or request Steam API credentials"""
        print("\n🔑 Setting up Steam API credentials...")

        # Check if .env file exists
        if os.path.exists(self.env_file):
            print("📄 Found existing .env file")
            try:
                with open(self.env_file, "r") as f:
                    content = f.read()

                # Parse .env file
                for line in content.split("\n"):
                    if line.startswith("STEAM_API_KEY="):
                        self.steam_api_key = line.split("=", 1)[1].strip()
                    elif line.startswith("STEAM_ID="):
                        self.steam_id = line.split("=", 1)[1].strip()

                if self.steam_api_key and self.steam_id:
                    print("✅ Found valid credentials in .env file")
                    return True

            except Exception as e:
                print(f"❌ Error reading .env file: {e}")

        # Request credentials from user
        print("\n📝 Steam API credentials needed:")
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
        while not self.steam_api_key:
            api_key = input("\nEnter your Steam API key: ").strip()
            if len(api_key) == 32 and all(
                c in "0123456789ABCDEF" for c in api_key.upper()
            ):
                self.steam_api_key = api_key
                print("✅ Valid API key format")
            else:
                print("❌ Invalid API key format (should be 32 hex characters)")

        # Get Steam ID
        while not self.steam_id:
            steam_id = input("Enter your Steam ID (17-digit number): ").strip()
            if steam_id.isdigit() and len(steam_id) == 17:
                self.steam_id = steam_id
                print("✅ Valid Steam ID format")
            else:
                print("❌ Invalid Steam ID format (should be 17 digits)")

        # Save to .env file
        try:
            with open(self.env_file, "w") as f:
                f.write(f"STEAM_API_KEY={self.steam_api_key}\n")
                f.write(f"STEAM_ID={self.steam_id}\n")
            print(f"✅ Credentials saved to {self.env_file}")
            return True

        except Exception as e:
            print(f"❌ Error saving credentials: {e}")
            return False

    def check_dependencies(self):
        """Check if required Python packages are installed"""
        print("\n📦 Checking Python dependencies...")

        # Check requests
        try:
            import requests

            print("✅ requests")
        except ImportError:
            print("❌ requests")
            if getattr(sys, "frozen", False):
                print("❌ Cannot install packages in executable mode")
                print("Please contact the developer about this packaging issue")
                return False
            else:
                install = input("\nInstall requests now? (y/n): ").strip().lower()
                if install == "y":
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "requests"]
                        )
                        print("✅ requests installed successfully")
                    except subprocess.CalledProcessError:
                        print("❌ Failed to install requests")
                        return False
                else:
                    return False

        # Check dotenv (optional)
        if DOTENV_AVAILABLE:
            print("✅ python-dotenv")
        else:
            print("⚠️ python-dotenv (optional - using alternative method)")

        # Check psutil (optional)
        if PSUTIL_AVAILABLE:
            print("✅ psutil")
        else:
            print("⚠️ psutil (optional - using alternative method)")

        print("✅ All essential dependencies are available")
        return True

    def run_main_script(self):
        """Run main.py to collect game data"""
        print("\n🎮 Running game data collection (main.py)...")
        print("This will scan your Steam library for games with achievements...")
        print("This may take several minutes depending on your library size.\n")

        try:
            # Run main.py with real-time output
            process = subprocess.Popen(
                [sys.executable, "main.py"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Print output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            result_code = process.poll()

            if result_code == 0:
                print("\n✅ Game data collection completed successfully")

                # Check if data.json was created
                if os.path.exists("data.json"):
                    try:
                        with open("data.json", "r", encoding="utf-8") as f:
                            data = json.load(f)
                            games_count = len(data.get("games", []))
                            print(
                                f"📊 Found {games_count} games with locked achievements"
                            )
                            return True
                    except Exception as e:
                        print(f"❌ Error reading data.json: {e}")
                        return False
                else:
                    print("❌ data.json not found after running main.py")
                    return False
            else:
                print("❌ Game data collection failed")
                return False

        except Exception as e:
            print(f"❌ Error running main.py: {e}")
            return False

    def run_achievement_unlocker(self):
        """Run steam_client_achievements.py to unlock achievements"""
        print("\n🏆 Running achievement unlocker (steam_client_achievements.py)...")
        print("This will unlock achievements in all games with locked achievements...")
        print("⚠️  WARNING: This process will modify your Steam achievements!")

        confirm = input("\nDo you want to proceed? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Achievement unlocking cancelled by user")
            return False

        try:
            # Run steam_client_achievements.py directly
            result = subprocess.run(
                [sys.executable, "steam_client_achievements.py"],
                capture_output=True,
                text=True,
            )
            
            # Print output from steam_client_achievements.py
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                print("\n✅ Achievement unlocking completed successfully")
                return True
            else:
                print("❌ Achievement unlocking failed")
                return False

        except Exception as e:
            print(f"❌ Error running steam_client_achievements.py: {e}")
            return False

    def cleanup_logs(self):
        """Optional cleanup of old log files"""
        print("\n🧹 Checking for old log files...")

        log_files = list(Path(".").glob("steam_achievement_log_*.txt"))

        if log_files:
            print(f"Found {len(log_files)} log files")
            cleanup = input("Remove old log files? (y/n): ").strip().lower()

            if cleanup == "y":
                removed_count = 0
                for log_file in log_files:
                    try:
                        log_file.unlink()
                        removed_count += 1
                    except Exception as e:
                        print(f"Could not remove {log_file}: {e}")

                print(f"✅ Removed {removed_count} log files")
        else:
            print("No old log files found")

    def run(self):
        """Main launcher execution"""
        self.print_header()

        # Step 1: Check Steam is running
        if not self.check_steam_running():
            return False

        # Step 2: Find Steam installation
        if not self.find_steam_path():
            print("\n❌ Cannot proceed without Steam installation")
            input("Press Enter to exit...")
            return False

        # Step 3: Check dependencies
        if not self.check_dependencies():
            print("\n❌ Cannot proceed without required dependencies")
            input("Press Enter to exit...")
            return False

        # Step 4: Get Steam credentials
        if not self.get_steam_credentials():
            print("\n❌ Cannot proceed without Steam credentials")
            input("Press Enter to exit...")
            return False

        # Step 5: Run main.py
        if not self.run_main_script():
            print("\n❌ Game data collection failed")
            input("Press Enter to exit...")
            return False

        # Step 6: Run steam_client_achievements.py
        if not self.run_achievement_unlocker():
            print("\n❌ Achievement unlocking failed")
            input("Press Enter to exit...")
            return False

        # Step 7: Optional cleanup
        self.cleanup_logs()

        # Success
        print("\n" + "=" * 60)
        print("🎉 STEAM ACHIEVEMENT UNLOCKER COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("📊 Check your Steam profile to see unlocked achievements")
        print("📝 Check the latest log file for detailed results")
        print("=" * 60)

        input("\nPress Enter to exit...")
        return True


def main():
    """Main entry point"""
    try:
        launcher = SteamLauncher()
        launcher.run()

    except KeyboardInterrupt:
        print("\n\n❌ Launcher interrupted by user")
        input("Press Enter to exit...")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        import traceback

        print(f"Full traceback:\n{traceback.format_exc()}")
        input("Press Enter to exit...")

    finally:
        # Always wait for user input before closing
        try:
            input("Press Enter to close...")
        except:
            import time

            time.sleep(10)  # Wait 10 seconds if input fails


if __name__ == "__main__":
    main()

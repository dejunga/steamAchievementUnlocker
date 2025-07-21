import ctypes
import os
import sys
import time
import winreg
from ctypes import (
    wintypes,
    POINTER,
    c_void_p,
    c_char_p,
    c_bool,
    c_int,
    c_uint32,
    c_uint64,
)


class SteamAchievementManager:
    """
    Steam Achievement Manager following the working C# implementation approach
    Uses steamclient.dll and proper Steam client interface hierarchy
    """

    # Class-level cache for DLL path to avoid repeated searches
    _cached_dll_path = None
    _cached_steam_path = None

    def __init__(self, app_id):
        self.app_id = str(app_id)
        self.steamclient = None
        self.steam_client = None
        self.steam_pipe = None
        self.steam_user = None
        self.user_stats = None
        self.user_stats_received = False
        self._initialize_steam(app_id)

    def _get_steam_install_path(self):
        """Get Steam installation path from Windows registry (with caching)"""
        # Use cached path if available
        if SteamAchievementManager._cached_steam_path:
            return SteamAchievementManager._cached_steam_path

        try:
            # Try both registry locations
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
                    # Cache the path for future use
                    SteamAchievementManager._cached_steam_path = install_path
                    return install_path
                except (WindowsError, FileNotFoundError):
                    continue

            # Fallback to common Steam paths
            common_paths = [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]

            for path in common_paths:
                if os.path.exists(os.path.join(path, "steamclient.dll")):
                    # Cache the path for future use
                    SteamAchievementManager._cached_steam_path = path
                    return path

            raise Exception("Could not find Steam installation")

        except Exception as e:
            raise Exception(f"Failed to get Steam install path: {e}")

    def _initialize_steam(self, app_id):
        """Initialize Steam client following C# implementation"""
        try:
            # Set Steam App ID environment variable
            os.environ["SteamAppId"] = str(app_id)

            # Get Steam installation path
            steam_path = self._get_steam_install_path()
            print(f"Found Steam at: {steam_path}")

            # Use cached DLL path if available
            if SteamAchievementManager._cached_dll_path:
                dll_path = SteamAchievementManager._cached_dll_path
                try:
                    # Set DLL directory for proper loading
                    if hasattr(ctypes.windll.kernel32, "SetDllDirectoryW"):
                        if "DLLs" in dll_path:
                            ctypes.windll.kernel32.SetDllDirectoryW(
                                os.path.dirname(dll_path)
                            )
                        else:
                            ctypes.windll.kernel32.SetDllDirectoryW(steam_path)

                    self.steamclient = ctypes.CDLL(dll_path)
                    print(f"Using cached DLL: {dll_path}")
                except Exception as e:
                    print(f"Cached DLL failed: {e}, trying fallback")
                    SteamAchievementManager._cached_dll_path = None  # Reset cache

            # If no cached path or cached path failed, try all paths
            if not self.steamclient:
                # Dynamic DLL search - works on any computer
                dll_paths = []

                # 1. Try current working directory first
                current_dir = os.getcwd()
                dll_paths.extend(
                    [
                        os.path.join(current_dir, "DLLs", "win64", "steam_api64.dll"),
                        os.path.join(current_dir, "DLLs", "steam_api64.dll"),
                        os.path.join(current_dir, "steam_api64.dll"),
                    ]
                )

                # 2. Try executable directory (for PyInstaller)
                if getattr(sys, "frozen", False):
                    # PyInstaller bundle directory
                    bundle_dir = getattr(
                        sys, "_MEIPASS", os.path.dirname(sys.executable)
                    )
                    dll_paths.extend(
                        [
                            os.path.join(
                                bundle_dir, "DLLs", "win64", "steam_api64.dll"
                            ),
                            os.path.join(bundle_dir, "DLLs", "steam_api64.dll"),
                            os.path.join(bundle_dir, "steam_api64.dll"),
                        ]
                    )

                    # Also try next to executable
                    exe_dir = os.path.dirname(sys.executable)
                    dll_paths.extend(
                        [
                            os.path.join(exe_dir, "DLLs", "win64", "steam_api64.dll"),
                            os.path.join(exe_dir, "DLLs", "steam_api64.dll"),
                            os.path.join(exe_dir, "steam_api64.dll"),
                        ]
                    )

                # 3. Try script directory (for development)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                dll_paths.extend(
                    [
                        os.path.join(script_dir, "DLLs", "win64", "steam_api64.dll"),
                        os.path.join(script_dir, "DLLs", "steam_api64.dll"),
                        os.path.join(script_dir, "steam_api64.dll"),
                    ]
                )

                # 4. Try Steam installation directory
                dll_paths.extend(
                    [
                        os.path.join(steam_path, "steamclient64.dll"),
                        os.path.join(steam_path, "steamclient.dll"),
                    ]
                )

                print(f"🔍 Searching for Steam DLLs in {len(dll_paths)} locations...")

                for dll_path in dll_paths:
                    print(f"  🔍 Checking: {dll_path}")
                    if os.path.exists(dll_path):
                        print(f"  ✅ Found DLL: {dll_path}")
                        try:
                            # Set DLL directory for proper loading
                            if hasattr(ctypes.windll.kernel32, "SetDllDirectoryW"):
                                if "DLLs" in dll_path:
                                    ctypes.windll.kernel32.SetDllDirectoryW(
                                        os.path.dirname(dll_path)
                                    )
                                else:
                                    ctypes.windll.kernel32.SetDllDirectoryW(steam_path)

                            self.steamclient = ctypes.CDLL(dll_path)
                            print(f"Successfully loaded: {dll_path}")
                            # Cache the successful path
                            SteamAchievementManager._cached_dll_path = dll_path
                            break
                        except Exception as e:
                            print(f"Failed to load {dll_path}: {e}")
                            continue

                if not self.steamclient:
                    raise Exception("Could not load any Steam DLL")

            # Handle different DLL types
            if "steam_api64.dll" in dll_path:
                # Use the working Steam API approach
                print("Using steam_api64.dll approach")
                try:
                    # Initialize Steam API
                    init_func = self.steamclient.SteamAPI_InitSafe
                    init_func.restype = c_bool

                    if not init_func():
                        raise Exception("SteamAPI_InitSafe failed")

                    # Get UserStats interface
                    get_userstats = self.steamclient.SteamAPI_SteamUserStats_v013
                    get_userstats.restype = c_void_p

                    self.user_stats = get_userstats()
                    if not self.user_stats:
                        raise Exception("Failed to get UserStats interface")

                    print("Steam API initialized successfully")
                    self._setup_steam_api_functions()
                    return

                except AttributeError as e:
                    print(f"Steam API approach failed: {e}")
                    # Fall through to Steam client approach

            # Steam client approach for steamclient64.dll
            try:
                create_interface = self.steamclient.CreateInterface
                create_interface.argtypes = [c_char_p, POINTER(c_int)]
                create_interface.restype = c_void_p

                # Create SteamClient018 interface (like C# code)
                version_ptr = c_int(0)
                self.steam_client = create_interface(
                    b"SteamClient018", ctypes.byref(version_ptr)
                )
                if not self.steam_client:
                    self.steam_client = create_interface(
                        b"SteamClient017", ctypes.byref(version_ptr)
                    )

                if not self.steam_client:
                    raise Exception("Failed to create SteamClient interface")

                print("Created SteamClient interface")

                # Set up Steam client vtable functions (like C# code)
                self._setup_steam_client_vtable()

                # Create Steam pipe (like C# Client.cs)
                self.steam_pipe = self._create_steam_pipe()
                if not self.steam_pipe:
                    raise Exception("Failed to create Steam pipe")
                print(f"Created Steam pipe: {self.steam_pipe}")

                # Connect to global user (like C# Client.cs)
                self.steam_user = self._connect_to_global_user()
                if not self.steam_user:
                    raise Exception("Failed to connect to global user")
                print(f"Connected to global user: {self.steam_user}")

                # Get UserStats interface through proper client context
                self.user_stats = self._get_user_stats_interface()
                if not self.user_stats:
                    raise Exception("Failed to get UserStats interface")
                print("Got UserStats interface through Steam client")

                # Setup UserStats function pointers
                self._setup_user_stats_interface()
                return

            except AttributeError:
                raise Exception("CreateInterface not available - wrong DLL?")

            print(f"Steam client initialized successfully for App ID: {app_id}")

        except Exception as e:
            self.cleanup()
            raise Exception(f"Failed to initialize Steam: {e}")

    def _setup_steam_client_vtable(self):
        """Setup Steam client vtable functions"""
        # Get Steam client vtable
        vtable = ctypes.cast(self.steam_client, POINTER(c_void_p)).contents
        vtable_funcs = ctypes.cast(vtable, POINTER(c_void_p * 30)).contents

        # Based on SteamClient018 interface layout from C# code
        # CreateSteamPipe (index 0)
        self._create_steam_pipe_func = ctypes.cast(
            vtable_funcs[0], ctypes.WINFUNCTYPE(c_int, c_void_p)
        )

        # BReleaseSteamPipe (index 1)
        self._release_steam_pipe_func = ctypes.cast(
            vtable_funcs[1], ctypes.WINFUNCTYPE(c_bool, c_void_p, c_int)
        )

        # ConnectToGlobalUser (index 2)
        self._connect_to_global_user_func = ctypes.cast(
            vtable_funcs[2], ctypes.WINFUNCTYPE(c_int, c_void_p, c_int)
        )

        # GetISteamUserStats (try different indices based on C# interface)
        # The exact index may vary, let's try index 11 which is common
        self._get_steam_user_stats_func = ctypes.cast(
            vtable_funcs[11],
            ctypes.WINFUNCTYPE(c_void_p, c_void_p, c_int, c_int, c_char_p),
        )

    def _create_steam_pipe(self):
        """Create Steam pipe for communication"""
        return self._create_steam_pipe_func(self.steam_client)

    def _connect_to_global_user(self):
        """Connect to global user"""
        return self._connect_to_global_user_func(self.steam_client, self.steam_pipe)

    def _get_user_stats_interface(self):
        """Get UserStats interface through Steam client context"""
        return self._get_steam_user_stats_func(
            self.steam_client,
            self.steam_user,
            self.steam_pipe,
            b"STEAMUSERSTATS_INTERFACE_VERSION013",
        )

    def _setup_steam_api_functions(self):
        """Setup Steam API function pointers"""
        try:
            # RequestUserStats
            self._request_user_stats_api = getattr(
                self.steamclient, "SteamAPI_ISteamUserStats_RequestUserStats", None
            )
            if self._request_user_stats_api:
                self._request_user_stats_api.argtypes = [c_void_p, c_uint64]
                self._request_user_stats_api.restype = c_uint64

            # SetAchievement
            self._set_achievement_api = getattr(
                self.steamclient, "SteamAPI_ISteamUserStats_SetAchievement", None
            )
            if self._set_achievement_api:
                self._set_achievement_api.argtypes = [c_void_p, c_char_p]
                self._set_achievement_api.restype = c_bool

            # ClearAchievement
            self._clear_achievement_api = getattr(
                self.steamclient, "SteamAPI_ISteamUserStats_ClearAchievement", None
            )
            if self._clear_achievement_api:
                self._clear_achievement_api.argtypes = [c_void_p, c_char_p]
                self._clear_achievement_api.restype = c_bool

            # StoreStats
            self._store_stats_api = getattr(
                self.steamclient, "SteamAPI_ISteamUserStats_StoreStats", None
            )
            if self._store_stats_api:
                self._store_stats_api.argtypes = [c_void_p]
                self._store_stats_api.restype = c_bool

            # RunCallbacks
            self._run_callbacks_api = getattr(
                self.steamclient, "SteamAPI_RunCallbacks", None
            )
            if self._run_callbacks_api:
                self._run_callbacks_api.restype = None

            # SteamAPI_Shutdown for cleanup
            self._shutdown_api = getattr(self.steamclient, "SteamAPI_Shutdown", None)
            if self._shutdown_api:
                self._shutdown_api.restype = None

            print("Steam API functions set up successfully")

        except Exception as e:
            raise Exception(f"Failed to setup Steam API functions: {e}")

    def _setup_user_stats_interface(self):
        """Setup UserStats interface function pointers"""
        try:
            # Get UserStats vtable
            vtable = ctypes.cast(self.user_stats, POINTER(c_void_p)).contents
            vtable_funcs = ctypes.cast(vtable, POINTER(c_void_p * 50)).contents

            # RequestUserStats (index 0)
            self._request_user_stats = ctypes.cast(
                vtable_funcs[0], ctypes.WINFUNCTYPE(c_bool, c_void_p, c_uint64)
            )

            # GetAchievement (index 1)
            self._get_achievement = ctypes.cast(
                vtable_funcs[1],
                ctypes.WINFUNCTYPE(c_bool, c_void_p, c_char_p, POINTER(c_bool)),
            )

            # SetAchievement (index 2)
            self._set_achievement = ctypes.cast(
                vtable_funcs[2], ctypes.WINFUNCTYPE(c_bool, c_void_p, c_char_p)
            )

            # ClearAchievement (index 3)
            self._clear_achievement = ctypes.cast(
                vtable_funcs[3], ctypes.WINFUNCTYPE(c_bool, c_void_p, c_char_p)
            )

            # StoreStats (index 5)
            self._store_stats = ctypes.cast(
                vtable_funcs[5], ctypes.WINFUNCTYPE(c_bool, c_void_p)
            )

            print("Using vtable functions for achievements")
        except Exception as e:
            raise Exception(f"Failed to setup UserStats interface: {e}")

    def request_user_stats(self, steam_id):
        """Request user stats and wait for callback"""
        try:
            print(f"Requesting user stats for Steam ID: {steam_id}")

            # Convert steam_id to uint64
            steam_id_uint64 = c_uint64(int(steam_id))

            # Use Steam API function if available (steam_api64.dll)
            if (
                hasattr(self, "_request_user_stats_api")
                and self._request_user_stats_api
            ):
                call_handle = self._request_user_stats_api(
                    self.user_stats, steam_id_uint64
                )
                if call_handle == 0:
                    raise Exception("RequestUserStats returned invalid call handle")
                print(f"RequestUserStats call handle: {call_handle}")

                # Wait for callback with RunCallbacks - optimized timing
                if hasattr(self, "_run_callbacks_api") and self._run_callbacks_api:
                    print("Waiting for callback with RunCallbacks...")
                    timeout = time.time() + 3.0  # Reduced from 5.0 to 3.0 seconds
                    while time.time() < timeout:
                        self._run_callbacks_api()
                        time.sleep(0.05)  # Reduced from 0.1 to 0.05 seconds
                else:
                    time.sleep(1.5)  # Reduced from 2 to 1.5 seconds

            # Use vtable function (steamclient64.dll)
            elif hasattr(self, "_request_user_stats"):
                result = self._request_user_stats(self.user_stats, steam_id_uint64)
                if not result:
                    raise Exception("Failed to request user stats")
                print("User stats requested, waiting for callback...")
                time.sleep(1.5)  # Reduced from 2 to 1.5 seconds
            else:
                print("Warning: No RequestUserStats function available")

            self.user_stats_received = True
            print("User stats received")
            return True

        except Exception as e:
            print(f"Error requesting user stats: {e}")
            return False

    def set_achievement(self, achievement_id, unlocked=True):
        """Set achievement state"""
        try:
            if not self.user_stats_received:
                print("Warning: User stats not received yet")

            print(
                f"Setting achievement '{achievement_id}' to {'unlocked' if unlocked else 'locked'}"
            )

            # Use Steam API functions if available (steam_api64.dll)
            if hasattr(self, "_set_achievement_api") and self._set_achievement_api:
                if unlocked:
                    result = self._set_achievement_api(
                        self.user_stats, achievement_id.encode("utf-8")
                    )
                else:
                    result = self._clear_achievement_api(
                        self.user_stats, achievement_id.encode("utf-8")
                    )
            # Use vtable functions (steamclient64.dll)
            elif hasattr(self, "_set_achievement"):
                if unlocked:
                    result = self._set_achievement(
                        self.user_stats, achievement_id.encode("utf-8")
                    )
                else:
                    result = self._clear_achievement(
                        self.user_stats, achievement_id.encode("utf-8")
                    )
            else:
                raise Exception("No achievement functions available")

            if result:
                print(
                    f"Achievement '{achievement_id}' {'unlocked' if unlocked else 'locked'} successfully"
                )
                return True
            else:
                print(
                    f"Failed to {'unlock' if unlocked else 'lock'} achievement '{achievement_id}'"
                )
                return False

        except Exception as e:
            print(f"Error setting achievement: {e}")
            return False

    def store_stats(self):
        """Store stats to Steam servers"""
        try:
            # Use Steam API function if available (steam_api64.dll)
            if hasattr(self, "_store_stats_api") and self._store_stats_api:
                result = self._store_stats_api(self.user_stats)
            # Use vtable function (steamclient64.dll)
            elif hasattr(self, "_store_stats"):
                result = self._store_stats(self.user_stats)
            else:
                raise Exception("No store stats function available")

            if result:
                print("Stats stored successfully")
                return True
            else:
                print("Failed to store stats")
                return False

        except Exception as e:
            print(f"Error storing stats: {e}")
            return False

    def unlock_achievement(self, achievement_id):
        """Convenience method to unlock achievement"""
        if self.set_achievement(achievement_id, True):
            return self.store_stats()
        return False

    def cleanup(self):
        """Cleanup Steam resources"""
        try:
            # For Steam API approach (steam_api64.dll)
            if hasattr(self, "_shutdown_api") and self._shutdown_api:
                print("Shutting down Steam API...")
                self._shutdown_api()
                print("Steam API shutdown complete")

            # For Steam client approach (steamclient64.dll)
            if (
                hasattr(self, "steam_pipe")
                and hasattr(self, "steam_client")
                and self.steam_pipe
                and self.steam_client
            ):
                if hasattr(self, "_release_steam_pipe_func"):
                    self._release_steam_pipe_func(self.steam_client, self.steam_pipe)
                    print("Released Steam pipe")

            # Clear environment variable
            if "SteamAppId" in os.environ:
                del os.environ["SteamAppId"]
                print("Cleared SteamAppId environment variable")

        except Exception as e:
            print(f"Error during cleanup: {e}")
            pass


def process_all_games():
    """Process all games from data.json and unlock all achievements"""
    import json

    # Load data from data.json
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(
            "Error: data.json not found. Please run main.py first to generate the data."
        )
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON in data.json")
        return

    steam_id = data["steam_id"]
    games = data["games"]

    print(f"Found {len(games)} games with achievements")
    print(f"Steam ID: {steam_id}")
    print("Starting batch achievement unlock process for ALL games...\n")

    total_achievements_unlocked = 0
    successful_games = 0
    failed_games = 0

    for i, game in enumerate(games, 1):
        app_id = game["appid"]
        game_name = game["name"]
        achievements = game["achievements"]

        # Skip games with no achievements
        if not achievements:
            print(f"Skipping {game_name} (no achievements)")
            continue

        # Only process games with unlockable achievements (achieved: 0 and not protected)
        locked_achievements = [ach for ach in achievements if ach["achieved"] == 0]
        unlockable_achievements = [
            ach for ach in locked_achievements if not ach.get("protected", False)
        ]
        protected_achievements = [
            ach for ach in locked_achievements if ach.get("protected", False)
        ]

        if not unlockable_achievements:
            if not locked_achievements:
                print(f"Skipping {game_name} (all achievements already unlocked)")
            else:
                print(
                    f"Skipping {game_name} ({len(protected_achievements)} locked achievements are all protected)"
                )
            continue

        print(f"[{i}/{len(games)}] Processing: {game_name} (App ID: {app_id})")
        print(
            f"  Achievements to unlock: {len(unlockable_achievements)} (skipping {len(protected_achievements)} protected)"
        )

        manager = None
        try:
            # Create Steam manager for this game (fresh initialization)
            print(f"  Initializing Steam API for {game_name}...")
            manager = SteamAchievementManager(app_id)

            # Request user stats first
            if manager.request_user_stats(steam_id):
                achievements_unlocked_this_game = 0

                # Unlock all unlockable achievements for this game
                for achievement in unlockable_achievements:
                    achievement_id = achievement["apiname"]

                    if manager.unlock_achievement(achievement_id):
                        achievements_unlocked_this_game += 1
                        total_achievements_unlocked += 1

                    # Removed delay between achievements for faster processing

                print(
                    f"  Successfully unlocked {achievements_unlocked_this_game}/{len(unlockable_achievements)} achievements"
                )
                successful_games += 1

            else:
                print(f"  Failed to request user stats for {game_name}")
                failed_games += 1

        except Exception as e:
            print(f"  Error processing {game_name}: {e}")
            failed_games += 1

        finally:
            # CRITICAL: Always cleanup Steam API completely for this game
            if manager:
                print(f"  Cleaning up Steam API for {game_name}...")
                manager.cleanup()

        # Wait between games to allow Steam to fully reset - optimized timing
        print(f"  Waiting 1 second for Steam to reset before next game...\n")
        time.sleep(1)  # Reduced from 3 to 1 second

    # Final summary
    print("=" * 50)
    print("BATCH UNLOCK SUMMARY")
    print("=" * 50)
    print(f"Total games processed: {successful_games + failed_games}")
    print(f"Successful games: {successful_games}")
    print(f"Failed games: {failed_games}")
    print(f"Total achievements unlocked: {total_achievements_unlocked}")
    print("=" * 50)

    # Keep program open until user closes it
    try:
        input("\nPress Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        print("\nProgram closing...")
    except Exception:
        print("Waiting 10 seconds before closing...")
        time.sleep(10)


if __name__ == "__main__":
    # Ask user what they want to do
    print("Steam Achievement Unlocker")
    print("1. Test single game (Beyond the Void)")
    print("2. Process all games from data.json")
    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        # Test with Beyond the Void
        app_id = 700570
        steam_id = "76561198195207346"
        achievement_ids = [
            "TURRET_BREAKER",
            "TOWER_DESTROYER",
        ]

        try:
            manager = SteamAchievementManager(app_id)

            # Request user stats first (critical step)
            if manager.request_user_stats(steam_id):
                # Unlock achievements
                for achievement_id in achievement_ids:
                    manager.unlock_achievement(achievement_id)
            else:
                print("Failed to request user stats")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            if "manager" in locals():
                manager.cleanup()

    elif choice == "2":
        # Process all games
        try:
            process_all_games()
        except KeyboardInterrupt:
            print("\n\nBatch processing interrupted by user.")
        except Exception as e:
            print(f"Error in batch processing: {e}")
    else:
        print("Invalid choice. Please run again and select 1 or 2.")

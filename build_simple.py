#!/usr/bin/env python3
"""
Simple build script without emojis for Windows compatibility
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller

        print("PyInstaller is installed")
        return True
    except ImportError:
        print("PyInstaller not found")
        print("Installing PyInstaller...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pyinstaller"]
            )
            print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("Failed to install PyInstaller")
            return False


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")

    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("Cleaned build directory")

    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("Cleaned dist directory")

    try:
        # Build using simple command
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onefile",
                "--console",
                "--add-data",
                "launcher.py;.",
                "--add-data",
                "steam_client_achievements.py;.",
                "--add-data",
                "steam_api64.dll;.",
                "--hidden-import",
                "requests",
                "--hidden-import",
                "dotenv",
                "--hidden-import",
                "urllib3",
                "--hidden-import",
                "chardet",
                "--hidden-import",
                "certifi",
                "--hidden-import",
                "idna",
                "--collect-all",
                "requests",
                "--collect-all",
                "dotenv",
                "--collect-submodules",
                "python-dotenv",
                "--name",
                "SteamAchievementUnlocker",
                "main.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("Executable built successfully")

            # Check if exe exists
            exe_path = Path("dist/SteamAchievementUnlocker.exe")
            if exe_path.exists():
                print(f"Executable created: {exe_path.absolute()}")
                return True
            else:
                print("Executable not found after build")
                return False
        else:
            print("Build failed")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except Exception as e:
        print(f"Error during build: {e}")
        return False


def main():
    """Main build process"""
    print("Steam Achievement Unlocker - Simple Build Script")
    print("=" * 50)

    # Check if required files exist
    required_files = ["launcher.py", "main.py", "steam_client_achievements.py", "steam_api64.dll"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Required file missing: {file}")
            return False

    print("All required files found")

    # Check PyInstaller
    if not check_pyinstaller():
        return False

    # Build executable
    if not build_executable():
        return False

    print("\n" + "=" * 50)
    print("BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("Your executable is ready in: dist/SteamAchievementUnlocker.exe")
    print("You can now distribute this single file to users")
    print("=" * 50)

    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

    input("\nPress Enter to exit...")

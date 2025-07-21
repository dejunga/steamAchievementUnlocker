# Steam Achievement Unlocker

A tool for unlocking Steam achievements across multiple games simultaneously.

## ⚠️ Important Notice

This tool is for educational and testing purposes only. Use at your own risk and in accordance with Steam's Terms of Service. The developers are not responsible for any consequences of using this software.

## 🚀 How to Use

1. Go to the `dist/` folder
2. Run `SteamAchievementUnlocker.exe`
3. Follow the on-screen prompts

**Requirements:**

- Steam must be installed and running on your system

## 📋 Features

- **Multi-threaded processing** - Unlock achievements across multiple games simultaneously
- **Dynamic Steam detection** - Automatically finds your Steam installation
- **Protected achievement filtering** - Skips achievements that shouldn't be unlocked
- **Progress tracking** - Real-time progress updates during processing
- **Steam API integration** - Uses official Steam client libraries
- **Error handling** - Comprehensive error handling and logging

## 🔧 How It Works

1. **Steam Detection**: Automatically locates Steam installation via Windows registry
2. **Game Scanning**: Retrieves list of games with locked achievements from Steam API
3. **Achievement Processing**: Uses Steam's internal API to unlock achievements
4. **Safety Checks**: Filters out protected/special achievements that shouldn't be modified

## 📁 Project Structure

```
├── main.py                     # Main application entry point
├── steam_client_achievements.py # Steam API interaction logic
├── steam_api64.dll            # Required Steam API library
├── build_simple.py            # Build script for creating executable
├── launcher.py                # Alternative launcher with additional features
├── requirements.txt           # Python dependencies
├── dist/                      # Pre-built executable (ready to use)
└── README.md                  # This file
```

## 🔍 Technical Details

### Dependencies

- **requests** - HTTP client for Steam Web API
- **python-dotenv** - Environment variable management (optional)

### System Requirements

- Windows 10/11
- Steam installed and configured
- Python 3.7+ (for source code usage)

### DLL Management

The application uses a hybrid approach:

- **Dynamic DLLs**: Automatically locates Steam system DLLs (`steamclient64.dll`, `tier0_s64.dll`, `vstdlib_s64.dll`) from your Steam installation
- **Bundled DLL**: Includes `steam_api64.dll` for consistent Steam API access

## 🐛 Troubleshooting

### Common Issues

**"Steam installation not found"**

- Ensure Steam is installed in a standard location
- Check Windows registry for Steam installation path

**"Failed to initialize Steam API"**

- Close Steam completely before running
- Run as administrator if needed
- Ensure Steam is properly installed

**"Module not found" errors**

- Install dependencies: `pip install -r requirements.txt`
- Use Python 3.7 or higher

## ⚖️ Legal & Ethics

This tool interacts with Steam's client API for educational and testing purposes. Users are responsible for:

- Complying with Steam's Terms of Service
- Understanding potential account risks
- Using the tool responsibly

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## 📄 License

This project is provided as-is for educational purposes. Use at your own discretion and risk.

---

**Note**: This tool was developed for learning about Steam's API and achievement systems. Always respect game developers and the intended gameplay experience.

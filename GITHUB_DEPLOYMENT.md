# GitHub Deployment Guide

## ✅ Project is Live on GitHub!

**Repository:** https://github.com/Arpit-Jindal-01/SNS-Project

## Download the App

### Option 1: Direct Download (Easiest)
1. Go to: https://github.com/Arpit-Jindal-01/SNS-Project/releases
2. Download **SNS-AudioProcessor.zip** (v1.0.0)
3. Extract the zip file
4. Double-click **SNS-AudioProcessor.app**

### Option 2: Clone and Build Locally
```bash
git clone https://github.com/Arpit-Jindal-01/SNS-Project.git
cd SNS-Project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build_executable.spec --clean
# App will be in dist/SNS-AudioProcessor.app
```

## How to Use

### Run the App
```bash
open dist/SNS-AudioProcessor.app
```

### Keyboard Controls
| Key | Function |
|-----|----------|
| `1` | Passthrough (no effect) |
| `2` | Echo effect |
| `3` | Robot effect |
| `4` | Pitch shift up |
| `5` | Pitch shift down |
| `6` | Noise gate |
| `↑`/`↓` | Adjust effect strength |
| `v` | Toggle visualization |
| `t` | Toggle test mode |
| `q` | Quit |

## Features

✅ **Real-Time Processing**
- Echo/reverb effect
- Robot/distortion effect
- Pitch shifting (±12 semitones)
- Noise gate for background noise

✅ **Visualization**
- Live waveform display
- Real-time effect indicators
- Amplitude monitoring

✅ **Professional Quality**
- Audio normalization to prevent clipping
- Optimized pipeline for low latency
- Clean architecture with modular effects

## Sharing with Others

### Option 1: Direct Link
Share this URL:
```
https://github.com/Arpit-Jindal-01/SNS-Project/releases
```

### Option 2: Discord/Slack
Post: "Download SNS Audio Processor: https://github.com/Arpit-Jindal-01/SNS-Project/releases/tag/v1.0.0"

### Option 3: Share the ZIP file
Users can download `SNS-AudioProcessor.zip` and extract it themselves.

## For Future Releases

### Automatic Builds
- GitHub Actions automatically builds new releases when you push a git tag
- Just commit your changes and push a new tag like `v1.0.1`
- The executable will be built and uploaded automatically

### Manual Build
```bash
cd /Users/arpitjindal/SNS\ Project
source .venv/bin/activate
rm -rf build dist
pyinstaller build_executable.spec --clean
```

### Upload New Release
```bash
cd dist
zip -r SNS-AudioProcessor.zip SNS-AudioProcessor.app
gh release create v1.0.1 SNS-AudioProcessor.zip --title "SNS Audio Processor v1.0.1" --notes "Updated version"
```

## Troubleshooting

### App won't open
```bash
xattr -d com.apple.quarantine "/path/to/SNS-AudioProcessor.app"
```

### No audio input
- Check System Preferences → Security & Privacy → Microphone
- Grant permission to the app on first launch

### Build failed
- Ensure Python 3.13+ is installed
- Run: `pip install -r requirements.txt`
- Delete `build/` and `dist/` folders
- Run: `pyinstaller build_executable.spec --clean`

## Project Structure

```
SNS-Project/
├── main.py              # Main application
├── effects.py           # Audio effect implementations
├── stream.py            # Audio I/O handler
├── requirements.txt     # Python dependencies
├── build_executable.spec # PyInstaller config
├── .github/workflows/   # CI/CD configuration
└── dist/               # Build output
    └── SNS-AudioProcessor.app  # Standalone app
```

## Version History

- **v1.0.0** (Apr 21, 2024) - Initial release
  - Real-time effects
  - Live visualization
  - macOS support

---

**Status**: ✅ Production Ready
**Platform**: macOS 10.13+
**Size**: ~135 MB

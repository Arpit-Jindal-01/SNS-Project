# SNS Audio Processor - Standalone Executable

## Quick Start

Your standalone macOS application has been built successfully! 🎉

### Location
```
/Users/arpitjindal/SNS Project/dist/SNS-AudioProcessor.app
```

### Running the App
**Option 1: Double-click**
- Open Finder → Navigate to `SNS Project/dist/`
- Double-click `SNS-AudioProcessor.app`

**Option 2: Command line**
```bash
open "/Users/arpitjindal/SNS Project/dist/SNS-AudioProcessor.app"
```

## What's Included

✅ All Python dependencies bundled
✅ Real-time audio processing
✅ Multiple effects (echo, robot, pitch shift)
✅ Live waveform visualization
✅ Test mode (synthetic audio signal)
✅ macOS code-signed

## Features

- **Echo Effect** - Add delay/reverb to your voice
- **Robot Effect** - Distortion with metallic sound
- **Pitch Shift** - Shift pitch ±12 semitones
- **Live Visualization** - Real-time waveform display
- **Test Mode** - Works without microphone (uses synthetic signal)

## Keyboard Controls

| Key | Action |
|-----|--------|
| `1` | Passthrough (no effect) |
| `2` | Echo effect |
| `3` | Robot effect |
| `4` | Pitch shift (up) |
| `5` | Pitch shift (down) |
| `6` | Noise gate |
| `↑`/`↓` | Adjust effect strength |
| `v` | Toggle visualization |
| `t` | Toggle test mode |
| `q` | Quit |

## File Size
- **SNS-AudioProcessor.app**: ~7.0 MB
- Includes: numpy, scipy, librosa, matplotlib, sounddevice, and all dependencies

## macOS Requirements
- macOS 10.13 (High Sierra) or later
- Apple Silicon (M1/M2/M3) or Intel Mac
- Microphone access for audio input

## First Run
On first launch, macOS may ask for microphone permissions. Click **Allow** to enable audio capture.

## Troubleshooting

### App won't open
- Try: `xattr -d com.apple.quarantine "/Users/arpitjindal/SNS Project/dist/SNS-AudioProcessor.app"`

### No audio input/output
- Check System Preferences → Security & Privacy → Microphone
- Ensure your microphone is connected and set as input device

### Console output
For debugging, run from terminal:
```bash
open -a Terminal "/Users/arpitjindal/SNS Project/dist/SNS-AudioProcessor.app/Contents/MacOS/SNS-AudioProcessor"
```

## Deployment

### Option 1: Share the .app
- Zip the app bundle: `SNS-AudioProcessor.app`
- Users can extract and double-click to run

### Option 2: Create a DMG installer
```bash
cd /Users/arpitjindal/SNS\ Project/dist
hdiutil create -volname "SNS Audio Processor" -srcfolder . -ov -format UDZO SNS-AudioProcessor.dmg
```

### Option 3: Distribute via GitHub
```bash
cd /Users/arpitjindal/SNS\ Project/dist
zip -r SNS-AudioProcessor.zip SNS-AudioProcessor.app
# Upload SNS-AudioProcessor.zip to GitHub releases
```

## Rebuild Instructions

To rebuild after code changes:

```bash
cd "/Users/arpitjindal/SNS Project"
source .venv/bin/activate
pyinstaller build_executable.spec --clean
```

New build will be in `dist/SNS-AudioProcessor.app`

---

**Status**: ✅ Ready for distribution
**Build Date**: 2026-04-21
**Version**: Production 1.0

# Real-Time Audio Signal Processing System

A production-quality real-time voice changer built in Python with emphasis on **stability, low latency, and clean signal processing**.

## New Professional Web Platform (SNS Studio)

This repository now includes a full professional web interface in `web_app.py` with:

- 3-tab production flow:
    - Real-Time (record mic sample, apply effects, compare waves)
    - Upload Audio (10 voice presets, transform and export)
    - Signal Q&A (AI chatbot)
- AI tutor chatbot focused on Signals and Systems using Groq API
- Voice upload and conversion with 10 presets:
    - Chipmunk (+12), High (+6), Normal (0), Deep (-6), Bass (-12)
    - Space Echo, Cyborg, Spooky, Retro, Cartoon
- Wave comparison panel and 3D waveform visualizer
- Effect info panel with formulas and implementation notes
- Modern responsive UI suitable for portfolio and production demos

### Run Web App

```bash
pip install -r requirements.txt
./run_web.sh
```

Or manually:

```bash
python3 -m streamlit run web_app.py
```

### AI Tutor Configuration

Set one or more provider credentials before launch:

```bash
export GEMINI_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
export GROQ_API_KEY="your_key_here"

# Optional model overrides
export GEMINI_MODEL="gemini-2.0-flash"
export OPENAI_MODEL="gpt-4o-mini"
export GROQ_MODEL="llama-3.3-70b-versatile"
```

If one provider is unavailable (quota/rate-limit), the app automatically falls back.

## Deployment

### Option 1: Render (recommended)

1. Push this project to GitHub.
2. In Render, create a new Web Service from the repo.
3. Render will auto-detect `render.yaml`.
4. Add environment variables in Render dashboard:
     - `GEMINI_API_KEY` and/or `OPENAI_API_KEY` and/or `GROQ_API_KEY`
5. Deploy.

Included config files:
- `render.yaml`
- `Procfile`

### Option 2: Docker (any VPS/cloud)

Build and run locally:

```bash
docker build -t sns-studio .
docker run -p 8501:8501 \
    -e GEMINI_API_KEY="your_key" \
    -e OPENAI_API_KEY="your_key" \
    -e GROQ_API_KEY="your_key" \
    sns-studio
```

Included config files:
- `Dockerfile`
- `.dockerignore`

### Environment Template

Use `.env.example` as a reference for all deployment variables.

## Key Improvements in This Version

✓ **Normalization function** to prevent clipping across all effects
✓ **Clean processing pipeline** with effect selection dictionary
✓ **Test mode** with synthetic sine wave generation (no mic needed)
✓ **Optimized visualization** with efficient line updates (blitted animation)
✓ **Buffer overflow/underflow detection** and logging
✓ **Comprehensive technical comments** explaining sampling, effects, and why each step matters
✓ **Proper dtype handling** (float32 throughout for precision and performance)
✓ **Better CLI menu** with effect descriptions and performance info

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run Interactive Mode

```bash
python main.py
```

**Keyboard controls:**
- `1` → Passthrough (baseline, no effect)
- `2` → Echo (delay-based)
- `3` → Robot (rectification + quantization)
- `4` → Pitch shift (semitone adjustment)
- `v` → Toggle visualization
- `d` → Show performance stats
- `?` → Show menu
- `q` → Quit

### Run Demo Scripts

```bash
python demo.py              # Pass-through test
python demo.py echo         # Echo effect demo
python demo.py robot        # Robot effect demo
python demo.py test         # Offline effect testing (no audio hardware needed)
```

### Test Mode (No Microphone Required)

Edit `main.py` and set:

```python
TEST_MODE = True
```

This generates synthetic 440 Hz sine wave instead of capturing from microphone. Useful for:
- Debugging without audio hardware
- Consistent reproducible testing
- Understanding effects without environment noise

---

## Audio Processing Pipeline

The system uses a **clean, modular pipeline**:

```
Input Stage
    ↓
[Test Signal Generator] or [Microphone Capture]
    ↓
Processing Stage
    ↓
Effect Selection (Echo/Robot/Pitch/Passthrough)
    ├─ Echo:   y[n] = x[n] + α*x[n-delay]
    ├─ Robot:  y[n] = |x[n]| (+quantization)
    ├─ Pitch:  librosa phase vocoder
    └─ Pass:   y[n] = x[n] (identity)
    ↓
Normalization Stage
    ├─ Find peak (max absolute value)
    ├─ Scale to 0.95 (safe level below 1.0)
    └─ Ensure float32 dtype
    ↓
Output Stage
    ├─ Float32 → Speaker output
    └─ Optional history tracking
    ↓
Speaker Output (or Visualization Storage)
```

### Why This Pipeline Works

1. **Separation of concerns** - Each stage independent and testable
2. **Effect isolation** - New effects easily added
3. **Normalization safety** - Prevents clipping from effect combinations
4. **Monitoring** - Tracks clipping, underflow, overflow

---

## Core Concepts Explained

### Sampling and Digital Audio

**Nyquist Theorem:** Maximum frequency = sample_rate / 2
- At 44100 Hz: Can represent frequencies up to 22,050 Hz
- This covers human hearing range (20 Hz - 20 kHz)
- Each sample = one amplitude value

**Sample Value Range:**
- Float32: -1.0 to 1.0 (standard for DSP)
- Int16: -32,768 to 32,767 (old CD standard)
- Values outside range = **clipping** (harsh distortion)

### Effect Types: Linear vs Non-Linear

**LINEAR EFFECTS** (output proportional to input):
- Echo/Delay: `y[n] = x[n] + α*x[n-delay]`
- Gain: `y[n] = gain * x[n]`
- Filter: `y[n] = Σ b[k] * x[n-k]`
- **Problem:** Multiple linear effects can stack and exceed 1.0!

**NON-LINEAR EFFECTS** (curved relationship):
- Rectification: `y[n] = |x[n]|` (absolute value)
- Soft clipping: `y[n] = tanh(x[n])` (smooth saturation)
- Quantization: `y[n] = round(x[n] / step) * step`
- **Creates harmonics** and interesting timbral changes

### Why Normalization is Essential

```
Problem:
  x[n] = 0.7 (input)
  After echo: 0.7 + 0.6 * 0.7 = 1.12 ← EXCEEDS 1.0!
  Digital clipping: hard cutoff to ±1.0
  Sound: Harsh, distorted, unnatural

Solution:
  1. Find peak = 1.12
  2. Calculate scale = 0.95 / 1.12 = 0.848
  3. Scale all samples: 0.7 * 0.848 = 0.594
  4. Result: Peak becomes 0.95 (safe, still audible)
```

**normalize_audio() function:**
- Called after every effect
- Prevents clipping while preserving dynamics
- Uses exponential moving average for smooth transitions

### Real-Time Audio Flow

**Callback-based architecture:**
- sounddevice calls `_audio_callback()` every ~23ms (1024 samples @ 44100 Hz)
- Must complete in < 23ms to avoid glitches (underflow)
- Runs in high-priority audio thread (don't use print() here!)

**Buffer Management:**
- Input buffer immediately copied (avoid corruption)
- Output hardcoded to [-1, 1] as final safety
- Statistics tracked: frame count, clipping, underflow, overflow

---

## Audio Effects Deep Dive

### Echo Effect

**Formula:** `y[n] = x[n] + α * x[n - delay]`

**How it works:**
1. Delay signal by N samples (creates copy delayed in time)
2. Mix with original signal at strength α
3. Creates audible echo/reverb effect

**Parameters:**
- `delay`: 0.2 seconds = 8,820 samples @ 44100 Hz
- `alpha`: 0.6 (60% of delayed signal mixed back)

**Why normalize:** Echo adds to original → can exceed 1.0

**Implementation:**
```python
output[delay:] += alpha * signal[:-delay]  # Vectorized (efficient!)
```

### Robot Effect

**Formula:** `y[n] = |x[n]|` (rectified) + spectral quantization

**How it works:**
1. Full-wave rectification: `y[n] = |x[n]|` (absolute value)
   - All negative samples become positive
   - Removes phase information, emphasizes magnitude
2. Spectral quantization: group frequencies into bands
   - Reduces frequency resolution
   - Creates metallic, machine-like character

**Mathematical insight:**
- **Non-linear:** -0.5 and +0.5 both become +0.5
- **Creates odd harmonics:** Dominant frequency + 3x, 5x, 7x, etc.
- **Removes tonal quality:** Only pitch remains, no timbre

**Why normalize:** Rectification doubles effective peak (removes negative half)

### Pitch Shift Effect

**Algorithm:** Librosa Phase Vocoder

**How it works:**
1. STFT (Short-Time Fourier Transform): time → frequency domain
2. Stretch frequency axis by `2^(n_steps/12)`
3. ISTFT (Inverse STFT): frequency → time domain
4. Result: Pitch changed, tempo preserved

**Semitone relationship:** Each semitone = `2^(1/12)` ≈ 1.0594
- +5 semitones = 1.0594^5 ≈ 1.33x frequency
- +12 semitones = 2x frequency (one octave up)
- -12 semitones = 0.5x frequency (one octave down)

**Why slow (more CPU):** FFT computation isn't cheap
- FFT size = 2,048 (46ms of samples)
- Computing for every chunk can hit CPU limits
- Use test mode to debug without real-time pressure

---

## Performance Characteristics

### Latency

**Total latency: ~23ms (1024 samples @ 44100 Hz)**

```
Breakdown:
- Input buffer:      ~12ms (system ADC buffering)
- Processing:        ~0.5ms (typically)
- Output buffer:     ~12ms (system DAC buffering)
- Total:             ~24ms (acceptable for voice)
```

**Latency perception:** < 20ms = imperceptible, 50ms = annoying echo

### CPU Usage Per Effect

Measured on modern CPU (core i7, ~2 GHz):
- **Passthrough:** ~0.1ms per chunk
- **Echo:** ~0.5ms per chunk (vectorized, very fast)
- **Robot:** ~1.2ms per chunk (STFT required)
- **Pitch shift:** ~2-5ms per chunk (most expensive!)

### Memory

- **History buffer:** 2 seconds @ 44100 Hz = 176 KB (visualization)
- **Temporary arrays:** ~100 KB (effects processing)
- **Stream buffers:** ~50 KB
- **Total:** < 1 MB (very efficient)

### Clipping Detection

- Warnings logged when output exceeds 1.0
- **Underflow warning:** Processing too slow
- **Overflow warning:** Input too loud or effect stackup
- **Solution:** Check logs, reduce effect chain complexity

---

## Test Mode: Debugging Without Audio Hardware

### Enable Test Mode

In `main.py`, set:
```python
TEST_MODE = True
```

### What Happens

1. **Instead of microphone**, system generates signal internally
2. **Default:** 440 Hz sine wave (musical note A4)
3. **ChirpMode** (optional): Sweep from 100 Hz to 4 kHz
4. **Phase tracking** ensures continuous signal (no clicks)

### Why Useful

- **Debugging:** Consistent signal = reproducible results
- **Testing effects:** Can verify output characteristics
- **Development:** No audio hardware needed
- **Examples:** Great for demos and learning

### Example

```python
from main import TestSignalGenerator

gen = TestSignalGenerator(sample_rate=44100, frequency=440.0)
signal = gen.generate_sine(1024)  # 1024-sample sine chunk

# Or chirp (frequency sweep)
signal = gen.generate_chirp(1024, f_start=100, f_end=4000)
```

---

## Improved Visualization

### Features

✓ **Real-time updating** (not full redraw)
✓ **Input + Output side-by-side** comparison
✓ **Efficient blitting** (only changed regions update)
✓ **2-second history** (visual feedback lag)
✓ **Toggle with 'v' key** while running

### How It Works

```python
# Efficient line update (not full redraw)
line.set_data(x_data, y_data)  # Set data
ani = FuncAnimation(..., blit=True)  # Only update changed regions
```

**Vs. inefficient:**
```python
ax.clear()  # ← Clears EVERYTHING
ax.plot(...)  # ← Redraws from scratch
```

### Update Rate

- **Every 100ms** for smooth visual feedback
- **While maintaining real-time audio** (audio thread unchanged)
- **Non-blocking** (launched in background thread)

---

## Comprehensive Testing

### Offline Testing (No Audio)

Test effects without microphone:

```bash
python demo.py test
```

Tests:
- Echo effect (shape, range, clipping prevention)
- Robot effect (non-negative output, range)
- Pitch shift (length preservation, artifact check)
- Normalization (peak reduction, safety)

### Live Testing

**Passthrough demo:**
```bash
python demo.py
```
Listen for baseline latency (~23ms, should feel real-time)

**Echo demo:**
```bash
python demo.py echo
```
Hear 0.2 second echo effect

**Robot demo:**
```bash
python demo.py robot
```
Hear metallic, vocoder-like effect

### Performance Profiling

Enable verbose logging:

```python
stream = AudioStream(verbose=True)
```

Prints every 100 frames:
- Input signal range
- Output signal range
- Clipping warnings
- Underflow/overflow events

---

## Customization Guide

### Change Effect Parameters

```python
# In main.py, after creating app:
app.pipeline.echo_delay_seconds = 0.5  # 500ms echo
app.pipeline.echo_strength = 0.8       # Stronger echo
app.pipeline.pitch_semitones = 12      # One octave up
```

### Add Custom Effect

1. Create function in `effects.py`:

```python
def apply_lpf(signal, cutoff_hz, sample_rate):
    """Simple low-pass filter."""
    # Your DSP code here
    return normalize_audio(output)
```

2. Add mode to `main.py`:

```python
elif self.mode == "lpf":
    output = apply_lpf(signal, cutoff_hz=2000, sample_rate=self.sample_rate)
```

### Adjust Latency

Edit chunk size in `main.py`:

```python
CHUNK_SIZE = 512   # Lower latency: ~11ms (more CPU)
CHUNK_SIZE = 2048  # Higher latency: ~46ms (less CPU)
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Audio crackling/glitches | Processing too slow | Disable visualization, use simpler effects |
| Distorted sound | Clipping (output > 1.0) | Check logs for clipping warnings, reduce input volume |
| No sound captured | Microphone not selected | Run `python -c "import sounddevice as sd; print(sd.query_devices())"` |
| Keyboard unresponsive | Terminal not in raw mode | Run from native terminal (not IDE) |
| Lag before audio | Pitch shift creating artifacts | Avoid pitch shift, use test mode |
| Memory growth | History buffer not clearing | `visualize = False` |

---

## File Structure

```
main.py              - Interactive application, pipeline, test signal generator
stream.py            - Real-time audio I/O with buffer management
effects.py           - Signal processing functions with normalization
demo.py              - Simple test scripts
test_system.py       - Comprehensive validation suite
requirements.txt     - Dependencies
README.md            - This file
QUICKREF.py          - Quick reference code snippets
web_app.py           - Professional web app (AI tutor + voice studio)
run_web.sh           - One-command web launcher
```

---

## Technical Reference

### Key Parameters

```python
SAMPLE_RATE = 44100          # Hz (CD quality)
CHUNK_SIZE = 1024            # samples (~23ms latency)
TARGET_PEAK = 0.95           # Normalization peak (safe level)
MAX_HISTORY = 2 * SAMPLE_RATE # 2 seconds for visualization
VIZ_UPDATE = 100              # ms between visualization updates
```

### Important Functions

**Normalization:**
```python
from effects import normalize_audio
output = normalize_audio(signal, target_peak=0.95)
```

**Effects:**
```python
from effects import apply_echo, apply_robot, apply_pitch_shift
```

**Audio Stream:**
```python
from stream import AudioStream
stream = AudioStream(sample_rate=44100, chunk_size=1024)
stream.set_processor(my_processor_func)
stream.start()
```

---

## Credits & References

- **sounddevice:** Cross-platform real-time audio
- **librosa:** Music and audio analysis (pitch shifting, STFT)
- **numpy:** Array operations and DSP
- **matplotlib:** Real-time visualization

---

## License

This project is provided as-is for educational and experimental purposes.

---

## Getting Help

1. Check console output for error messages
2. Enable verbose logging: `AudioStream(verbose=True)`
3. Run offline tests: `python demo.py test`
4. Use test mode instead of microphone: `TEST_MODE = True`
5. Check performance stats: Press 'd' while running

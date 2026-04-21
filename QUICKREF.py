"""Quick reference guide for the real-time voice changer system."""

# QUICK START
# ===========
# python main.py              # Start interactive voice changer
# python test_system.py       # Run validation tests
# python demo.py              # Simple pass-through demo


# KEYBOARD CONTROLS
# =================
# 1         → Echo effect
# 2         → Robot effect
# 3         → Pitch shift
# v         → Toggle visualization
# d         → Show statistics
# q         → Quit


# CORE FUNCTIONS (from effects.py)
# =================================

# Echo effect: y[n] = x[n] + alpha * x[n - delay]
from effects import apply_echo
output = apply_echo(signal, delay=8820, alpha=0.6)

# Robot effect: y[n] = |x[n]| (normalized)
from effects import apply_robot
output = apply_robot(signal)

# Pitch shift: Shift by n_steps semitones
from effects import apply_pitch_shift
output = apply_pitch_shift(signal, sample_rate=44100, n_steps=5)


# REAL-TIME STREAMING
# ====================

from stream import AudioStream
from effects import apply_echo

# Create audio stream
stream = AudioStream(sample_rate=44100, chunk_size=1024)

# Set processing function
def my_processor(audio):
    return apply_echo(audio, delay=8820, alpha=0.6)

stream.set_processor(my_processor)

# Start streaming
stream.start()

# Keep running...
import time
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pass

# Stop streaming
stream.stop()


# CUSTOMIZE EFFECTS
# =================

from main import RealTimeVoiceChanger

app = RealTimeVoiceChanger()

# Adjust echo parameters
app.echo_delay_samples = int(0.5 * 44100)  # 0.5s delay
app.echo_alpha = 0.8

# Adjust pitch shift
app.pitch_steps = 7  # 7 semitones higher
# or app.pitch_steps = -12  # One octave lower

# Run
app.run()


# SIGNAL PROCESSING DETAILS
# ==========================

# Echo (y[n] = x[n] + α*x[n-delay])
# delay: samples to delay (int)
# alpha: echo strength [0.0, 1.0]
# Example: 0.2s @ 44100 Hz = 8820 samples

# Robot (y[n] = |x[n]|)
# Full-wave rectification
# Auto-normalized to prevent clipping
# Creates metallic/vocoder sound

# Pitch (librosa phase vocoder)
# n_steps: semitones to shift
# Positive = higher, Negative = lower
# Example: ±12 = one octave


# PERFORMANCE SPECS
# =================
# Latency: ~23ms (1024 samples @ 44100 Hz)
# CPU: ~0.5-2ms per frame (depends on effect)
# Memory: ~176KB (2s history for visualization)
# Keyboard poll: 10ms
# Visualization update: 100ms


# LOGGING
# =======

import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose stream logging
stream = AudioStream(verbose=True)

# See logs for:
# - Stream startup/shutdown
# - Mode switches
# - Clipping warnings
# - Frame counts
# - Performance stats


# TESTING
# =======

# Run validation tests
# python test_system.py

# Tests:
# - Echo effect
# - Robot effect
# - Pitch shift
# - Edge cases (silent, loud, short signals)
# - Real-time chunk processing
# - Stream setup


# TROUBLESHOOTING
# ===============

# No audio?
# 1. Check devices: python -c "import sounddevice as sd; print(sd.query_devices())"
# 2. Check microphone in OS settings
# 3. Look for error messages in main.py output

# Distorted audio?
# 1. Reduce microphone volume
# 2. Check console for clipping warnings
# 3. Reduce output volume

# Keyboard not working?
# 1. Run from native terminal (not IDE)
# 2. macOS: Grant terminal Full Disk Access if needed
# 3. Windows: Try Administrator mode

# High CPU?
# 1. Press 'v' to disable visualization
# 2. Avoid pitch shift (most expensive)
# 3. Increase chunk_size for lower latency trade-off


# ARCHITECTURE OVERVIEW
# =====================

# main.py
#   - RealTimeVoiceChanger class
#   - Mode switching (echo/robot/pitch)
#   - Keyboard input (non-blocking thread)
#   - Visualization (optional matplotlib)
#   - Statistics tracking

# stream.py
#   - AudioStream class
#   - Real-time callback for audio I/O
#   - Clipping detection
#   - Frame/event counting

# effects.py
#   - apply_echo() - y[n] = x[n] + α*x[n-delay]
#   - apply_robot() - y[n] = |x[n]| (normalized)
#   - apply_pitch_shift() - librosa phase vocoder
#   - PassThroughEffect - identity function

# demo.py
#   - Simple demos for testing

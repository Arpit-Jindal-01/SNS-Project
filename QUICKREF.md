"""QUICK START GUIDE - Real-Time Voice Changer"""

# ============================================================================
# INSTALLATION
# ============================================================================

# pip install -r requirements.txt


# ============================================================================
# RUNNING
# ============================================================================

# Interactive mode (real-time effect switching)
# $ python main.py

# Simple pass-through (no effect, baseline latency)
# $ python demo.py

# Echo effect demo
# $ python demo.py echo

# Robot effect demo
# $ python demo.py robot

# Offline effect testing (no audio hardware needed)
# $ python demo.py test


# ============================================================================
# KEYBOARD CONTROLS (while running main.py)
# ============================================================================

# 1     - Passthrough (no effect)
# 2     - Echo effect (y[n] = x[n] + 0.6*x[n-delay])
# 3     - Robot effect (full-wave rectification)
# 4     - Pitch shift (±5 semitones)
# v     - Toggle visualization
# d     - Show performance statistics
# ?     - Show menu
# q     - Quit
# Ctrl+C - Force quit


# ============================================================================
# TEST MODE - DEBUGGING WITHOUT MICROPHONE
# ============================================================================

# In main.py, change:
#   TEST_MODE = False  →  TEST_MODE = True
#
# Then run: python main.py
#
# System will generate 440 Hz sine wave instead of using microphone
# Useful for debugging, testing effects, understanding system behavior


# ============================================================================
# CORE CONCEPTS
# ============================================================================

SAMPLING_FORMULA = """
y[n] = processed sample at index n
Nyquist limit = sample_rate / 2
At 44100 Hz: max frequency = 22050 Hz (Nyquist)
"""

ECHO_FORMULA = """
y[n] = x[n] + α * x[n - delay]
Linear processing: adds delayed copy to original
Must normalize to prevent clipping!
"""

ROBOT_FORMULA = """
y[n] = |x[n]| + spectral quantization
Non-linear: rectification (absolute value)
Creates odd harmonics (metallic sound)
"""

PITCH_FORMULA = """
New frequency = Old frequency * 2^(n_steps/12)
+5 semitones ≈ 1.33x frequency
+12 semitones = 2x frequency (octave up)
-12 semitones = 0.5x frequency (octave down)
"""

NORMALIZATION_FORMULA = """
1. Find peak = max(|signal|)
2. If peak > target_peak:
     output = signal * (target_peak / peak)
3. Result: prevents clipping while preserving dynamics
"""


# ============================================================================
# WHY NORMALIZATION IS CRITICAL
# ============================================================================

"""
Without normalization:
  Input:     0.7
  After echo (α=0.6, delay filled): 0.7 + 0.42 = 1.12
  Result: CLIPPING at ±1.0 → Harsh distortion!

With normalization:
  1. Detect peak = 1.12
  2. Scale factor = 0.95 / 1.12 = 0.848
  3. Output: 0.7 * 0.848 = 0.594 (safe!)
  4. Echo creates 0.594 + 0.3564 = 0.95 (just safe)

Normalization prevents:
- Clipping (hard cutoff distortion)
- Unexpected volume changes
- Effect combinations causing artifacts
"""


# ============================================================================
# CODE EXAMPLES
# ============================================================================

# Example 1: Simple echo using the system
from stream import AudioStream
from effects import apply_echo

stream = AudioStream(sample_rate=44100, chunk_size=1024)

def echo_processor(audio):
    delay_samples = int(0.2 * 44100)  # 0.2 seconds
    return apply_echo(audio, delay=delay_samples, alpha=0.6)

stream.set_processor(echo_processor)
stream.start()

# ... keep running ...

# stream.stop()


# Example 2: Test effect offline (no audio hardware)
from effects import apply_echo, normalize_audio
import numpy as np

# Generate test signal
duration = 0.1  # 100ms
t = np.linspace(0, duration, int(44100 * duration))
signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)

# Apply echo
output = apply_echo(signal, delay=8820, alpha=0.6)

# Check result
print(f"Input: {signal.min():.3f} to {signal.max():.3f}")
print(f"Output: {output.min():.3f} to {output.max():.3f}")
print(f"Clipping: {np.any(np.abs(output) > 1.0)}")


# Example 3: Custom effect
from effects import normalize_audio
import numpy as np

def apply_gain(signal, gain=0.5):
    """Simple gain/volume effect."""
    output = signal * gain
    return normalize_audio(output)

# Use in pipeline
from main import RealTimeVoiceChanger
app = RealTimeVoiceChanger()
# ... add custom effect to pipeline ...


# ============================================================================
# AUDIO PROCESSING PIPELINE
# ============================================================================

"""
Input Stage
    ↓
Microphone capture (or test sine wave)
    ↓
Effect Selection (echo/robot/pitch/passthrough)
    ↓
Normalization: Scale to prevent clipping
    ↓
Ensure float32 dtype
    ↓
Final clip to [-1, 1] (safety)
    ↓
Speaker output
    ↓
Optional visualization (history storage)
"""


# ============================================================================
# LATENCY BREAKDOWN
# ============================================================================

"""
At 44100 Hz sample rate, 1024 chunk size:

Chunk latency = 1024 samples / 44100 Hz = ~23.2 ms

System latency components:
- Input buffering (ADC):       ~12 ms
- Processing (callback):       ~0.5 ms (typically)
- Output buffering (DAC):      ~12 ms
- Total round-trip:            ~24.5 ms

This is imperceptible to humans (threshold ~50 ms)
"""


# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

"""
For LOWER latency (more CPU):
  CHUNK_SIZE = 512    # ~11ms instead of 23ms
  Costs: More CPU overhead, more callbacks per second
  Risk: Glitches if CPU can't keep up

For LOWER CPU (higher latency):
  CHUNK_SIZE = 2048   # ~46ms instead of 23ms
  Benefit: Less CPU, smoother
  Cost: More noticeable delay

Profile performance:
  1. Run with verbose=True
  2. Check logs for clipping/underflow warnings
  3. Use statistics output (press 'd')
  4. Pitch shift is most CPU expensive
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Audio crackling?
#   → Disable visualization (press 'v')
#   → Check CPU usage (use external tools)
#   → Increase chunk size (less real-time, less CPU load)

# Distorted sound?
#   → Check console for clipping warnings
#   → Reduce microphone volume
#   → Reduce effect strength (echo alpha, etc.)

# No audio input?
#   → List devices: python -c "import sounddevice as sd; print(sd.query_devices())"
#   → Check microphone is not muted
#   → Try specifying device IDs explicitly

# Keyboard not working?
#   → Run from native terminal (not IDE if possible)
#   → Use test mode for development (TEST_MODE = True)

# Visualization laggy?
#   → Disable with 'v' key
#   → Close other visual applications
#   → matplotlib rendering can be slow


# ============================================================================
# STATISTICS INTERPRETATION
# ============================================================================

"""
Performance output (press 'd'):

  echo        | Chunks: 12500  | Avg time:  0.45 ms
  robot       | Chunks:  8750  | Avg time:  1.20 ms
  pitch       | Chunks:  3750  | Avg time:  2.15 ms

Interpretation:
  - "Chunks": How many 1024-sample chunks processed in this mode
  - "Avg time": Average processing time per chunk
  - Safe limit: Must be < 23ms per chunk (1024 @ 44100 Hz) for real-time
    (actual margin ~20ms, but fast effects should be < 2ms)

Issues:
  - Avg time > 2ms for simple effects = something wrong
  - Avg time > 5ms for pitch shift = normal, but risky under load
  - Uneven distribution = effects have compatibility issues
"""


# ============================================================================
# FURTHER READING
# ============================================================================

"""
Digital Signal Processing (DSP) Basics:
  - Nyquist-Shannon Sampling Theorem
  - Frequency domain vs time domain
  - FFT (Fast Fourier Transform)
  - Phase vocoder (used for pitch shifting)

Audio Production:
  - Clipping and digital distortion
  - Normalization and compression
  - Latency in real-time systems

Real-Time Computing:
  - Audio callbacks and thread safety
  - Buffer management
  - Priority interrupts

References:
  - librosa documentation: https://librosa.org/
  - sounddevice documentation: https://python-sounddevice.readthedocs.io/
  - numpy DSP tutorials: various online courses
"""


# ============================================================================
# FILE ORGANIZATION
# ============================================================================

"""
effects.py
  - normalize_audio()      : Core normalization function
  - apply_echo()           : Echo effect implementation
  - apply_robot()          : Robot/rectification effect
  - apply_pitch_shift()    : Pitch shifting via librosa
  - apply_passthrough()    : Identity effect

stream.py
  - AudioStream class      : Real-time I/O management
  - _audio_callback()      : Called every chunk
  - Buffer/overflow handling
  - Clipping detection

main.py
  - AudioProcessingPipeline: Clean effect selection
  - TestSignalGenerator    : Synthetic signal generation
  - RealTimeVoiceChanger   : Main application
  - Keyboard input handler
  - Visualization setup

demo.py
  - simple_passthrough()   : Basic test
  - echo_demo()            : Echo effect demo
  - robot_demo()           : Robot effect demo
  - test_offline_effects() : No-audio testing
"""

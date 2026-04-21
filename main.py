"""Real-time voice changer with test mode, optimized visualization, and clean pipeline.

AUDIO PROCESSING PIPELINE:
1. Input Stage: Capture from microphone OR generate test signal
2. Processing Stage: Apply selected effect (echo, robot, pitch)
3. Normalization: Ensure output stays in [-1, 1] to prevent clipping
4. Output Stage: Send to speakers OR store for visualization
5. Visualization: Optional real-time waveform display

TEST MODE:
- Generates synthetic sine wave instead of using microphone
- Useful for debugging without audio hardware dependency
- Consistent test signal allows effect verification
"""

import numpy as np
from stream import AudioStream
from effects import apply_echo, apply_robot, apply_pitch_shift, apply_passthrough, normalize_audio, apply_noise_gate
import threading
import queue
import time
import logging
from collections import deque
import sys

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# TEST MODE: Set to True to use generated sine wave instead of microphone
TEST_MODE = True

# Sample rate (Hz) - 44100 is standard for audio
SAMPLE_RATE = 44100

# Chunk size (samples) - affects latency
# 1024 samples @ 44100 Hz = ~23ms latency
CHUNK_SIZE = 1024

# Maximum history for visualization (2 seconds of audio)
MAX_HISTORY = 2 * SAMPLE_RATE

# Visualization update interval (milliseconds)
VIZ_UPDATE_INTERVAL = 100

# Try to import matplotlib (optional for visualization)
try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("⚠ matplotlib not available - visualization disabled")


# ============================================================================
# AUDIO PROCESSING PIPELINE
# ============================================================================

class AudioProcessingPipeline:
    """Clean audio processing pipeline with effect selection."""

    # Effect dictionary - maps mode names to processing functions
    EFFECTS = {
        "passthrough": apply_passthrough,
        "echo": None,  # Initialized with parameters
        "robot": apply_robot,
        "pitch": None,  # Initialized with parameters
    }

    def __init__(self, sample_rate=44100):
        """Initialize pipeline with effect parameters."""
        self.sample_rate = sample_rate

        # Noise gate parameters
        self.noise_gate_enabled = True
        self.noise_gate_threshold = 0.02  # 2% of full scale (good default)

        # Effect parameters (easily configurable)
        self.echo_delay_seconds = 0.2
        self.echo_strength = 0.6
        self.pitch_semitones = 5

    def process(self, signal, mode):
        """Process signal through pipeline: gate → effect → normalize.

        PIPELINE STAGES:
        1. Noise Gate: Remove signals below threshold
        2. Effect: Apply selected effect (echo, robot, pitch, pass)
        3. Normalization: Ensure signal in safe range [-1, 1]

        Args:
            signal: numpy array of audio samples
            mode: effect mode ("passthrough", "echo", "robot", "pitch")

        Returns:
            Processed and normalized audio array
        """
        try:
            # STAGE 1: NOISE GATE (before effects!)
            # Remove background noise before processing
            if self.noise_gate_enabled:
                output = apply_noise_gate(signal, threshold=self.noise_gate_threshold)
            else:
                output = signal.copy().astype(np.float32)

            # STAGE 2: EFFECT PROCESSING
            # Select and apply effect based on mode
            if mode == "passthrough":
                output = apply_passthrough(output)

            elif mode == "echo":
                # Delay is specified in samples
                delay_samples = int(self.echo_delay_seconds * self.sample_rate)
                output = apply_echo(output, delay=delay_samples, alpha=self.echo_strength)

            elif mode == "robot":
                output = apply_robot(output, num_bands=8)

            elif mode == "pitch":
                output = apply_pitch_shift(output, self.sample_rate, self.pitch_semitones)

            else:
                # Unknown mode - passthrough
                output = apply_passthrough(output)

            # STAGE 3: NORMALIZATION (final safety)
            # Ensure normalized (effects should normalize, but this is final safety)
            output = normalize_audio(output, target_peak=0.95)

            return output

        except Exception as e:
            logger.error(f"Pipeline error (mode={mode}): {e}")
            # On error, return input unchanged to avoid audio dropout
            return signal.astype(np.float32)


# ============================================================================
# TEST SIGNAL GENERATION
# ============================================================================

class TestSignalGenerator:
    """Generate synthetic test signals for debugging without audio hardware."""

    def __init__(self, sample_rate=44100, frequency=440.0):
        """Initialize test signal generator.

        Args:
            sample_rate: Sample rate in Hz (default 44100)
            frequency: Test signal frequency in Hz (default 440 = A4 note)
        """
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.phase = 0.0  # Track phase for continuous generation

    def generate_sine(self, num_samples):
        """Generate sine wave: y = sin(2π * f * t)

        SINE WAVE FORMULA:
        - y[n] = sin(2π * frequency * n / sample_rate)
        - 2π = full cycle (360 degrees)
        - frequency = cycles per second (Hz)
        - n = sample index (0, 1, 2, ...)

        Args:
            num_samples: Number of samples to generate

        Returns:
            numpy array of sine wave samples
        """
        # Generate time array
        t = (np.arange(num_samples) + self.phase) / self.sample_rate

        # Generate sine wave
        signal = np.sin(2 * np.pi * self.frequency * t).astype(np.float32)

        # Update phase for continuous generation (avoid clicks between chunks)
        self.phase += num_samples

        return signal

    def generate_chirp(self, num_samples, f_start=100, f_end=4000):
        """Generate chirp (frequency sweep) signal.

        CHIRP (FREQUENCY SWEEP):
        - Frequency linearly increases from f_start to f_end
        - Useful for testing effects across frequency range
        - Allows verification of frequency-dependent processing

        Args:
            num_samples: Number of samples to generate
            f_start: Starting frequency in Hz
            f_end: Ending frequency in Hz

        Returns:
            numpy array of chirp signal
        """
        t = np.arange(num_samples) / self.sample_rate

        # Frequency sweep: f(t) = f_start + (f_end - f_start) * t / duration
        duration = num_samples / self.sample_rate
        frequency = f_start + (f_end - f_start) * t / duration

        # Phase integral: phase(t) = 2π * ∫ f(τ) dτ
        # For linear chirp: phase = 2π * (f_start*t + (f_end-f_start)*t^2 / (2*duration))
        phase = 2 * np.pi * (f_start * t + (f_end - f_start) * t * t / (2 * duration))

        signal = np.sin(phase).astype(np.float32)
        self.phase += num_samples

        return signal


# ============================================================================
# REAL-TIME VOICE CHANGER APPLICATION
# ============================================================================

class RealTimeVoiceChanger:
    """Real-time voice changer with effect switching and visualization."""

    def __init__(self, sample_rate=44100, chunk_size=1024, test_mode=False):
        """Initialize voice changer.

        Args:
            sample_rate: Sample rate in Hz
            chunk_size: Audio chunk size in samples
            test_mode: Use generated signal instead of microphone
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.test_mode = test_mode

        # Audio processing pipeline
        self.pipeline = AudioProcessingPipeline(sample_rate)

        # Current effect mode
        self.mode = "passthrough"  # Start with passthrough

        # Audio stream
        self.audio_stream = AudioStream(
            sample_rate=sample_rate,
            chunk_size=chunk_size,
            verbose=False
        )

        # Test signal generator (only used if test_mode=True)
        self.test_generator = TestSignalGenerator(sample_rate, frequency=440.0)

        # Keyboard input (non-blocking)
        self.input_queue = queue.Queue()
        self.keyboard_thread = None
        self.running = False

        # Signal history for visualization
        self.input_history = deque(maxlen=MAX_HISTORY)
        self.output_history = deque(maxlen=MAX_HISTORY)
        self.visualize = False

        # Statistics per mode
        self.stats = {mode: {"count": 0, "avg_time": 0} for mode in self.pipeline.EFFECTS}

    def process_audio(self, audio_input):
        """Main audio processing callback - called for each chunk.

        This is the core real-time processing function called by AudioStream.
        Must be fast to avoid audio glitches.

        Args:
            audio_input: numpy array of input samples

        Returns:
            numpy array of processed samples
        """
        start_time = time.perf_counter()

        try:
            # Process through pipeline
            output = self.pipeline.process(audio_input, self.mode)

            # Track history for visualization
            if self.visualize:
                self.input_history.extend(audio_input)
                self.output_history.extend(output)

            # Update statistics (exponential moving average)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.stats[self.mode]["count"] += 1
            self.stats[self.mode]["avg_time"] = (
                self.stats[self.mode]["avg_time"] * 0.9 + elapsed_ms * 0.1
            )

            return output

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return audio_input.astype(np.float32)

    def _read_keyboard(self):
        """Non-blocking keyboard input reader (runs in separate daemon thread).

        Captures keyboard input without blocking audio processing.
        Platform-specific implementation for macOS, Windows, Linux.
        """
        if sys.platform == "darwin":
            # macOS: Use raw terminal mode
            import tty
            import termios

            try:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(fd)

                while self.running:
                    try:
                        ch = sys.stdin.read(1)
                        if ch:
                            self.input_queue.put(ch.lower())
                    except (EOFError, OSError):
                        pass
                    time.sleep(0.01)
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

        elif sys.platform == "win32":
            # Windows: Use msvcrt
            try:
                import msvcrt
                while self.running:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch().decode().lower()
                        self.input_queue.put(ch)
                    time.sleep(0.01)
            except ImportError:
                logger.warning("Keyboard input not supported on this platform")
        else:
            # Linux: Try msvcrt, fall back to warning
            try:
                import msvcrt
                while self.running:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch().decode().lower()
                        self.input_queue.put(ch)
                    time.sleep(0.01)
            except ImportError:
                logger.warning("Keyboard input may not work on this platform")

    def _handle_input(self):
        """Handle keyboard commands for mode switching and control."""
        while not self.input_queue.empty():
            try:
                key = self.input_queue.get_nowait()

                # Effect modes
                if key == "1":
                    self.mode = "passthrough"
                    logger.info(f"✓ Mode: PASSTHROUGH (no effect)")

                elif key == "2":
                    self.mode = "echo"
                    delay_s = self.pipeline.echo_delay_seconds
                    strength = self.pipeline.echo_strength
                    logger.info(f"✓ Mode: ECHO (delay: {delay_s:.2f}s, strength: {strength})")

                elif key == "3":
                    self.mode = "robot"
                    logger.info(f"✓ Mode: ROBOT (full-wave rectification)")

                elif key == "4":
                    self.mode = "pitch"
                    semitones = self.pipeline.pitch_semitones
                    logger.info(f"✓ Mode: PITCH SHIFT ({semitones:+d} semitones)")

                # Controls
                elif key == "v":
                    self.visualize = not self.visualize
                    status = "ON" if self.visualize else "OFF"
                    logger.info(f"Visualization: {status}")

                elif key == "d":
                    self._print_stats()

                elif key == "q":
                    logger.info("Quit requested")
                    return False

                elif key == "?":
                    self._print_menu()

                # Noise gate controls
                elif key == "g":
                    self.pipeline.noise_gate_enabled = not self.pipeline.noise_gate_enabled
                    status = "ON" if self.pipeline.noise_gate_enabled else "OFF"
                    threshold = self.pipeline.noise_gate_threshold
                    logger.info(f"Noise gate: {status} (threshold: {threshold:.3f})")

                elif key == "+":
                    # Increase threshold (less noise removal)
                    self.pipeline.noise_gate_threshold = min(
                        self.pipeline.noise_gate_threshold + 0.01, 0.5
                    )
                    logger.info(f"Noise gate threshold: {self.pipeline.noise_gate_threshold:.3f}")

                elif key == "-":
                    # Decrease threshold (more noise removal)
                    self.pipeline.noise_gate_threshold = max(
                        self.pipeline.noise_gate_threshold - 0.01, 0.001
                    )
                    logger.info(f"Noise gate threshold: {self.pipeline.noise_gate_threshold:.3f}")

            except queue.Empty:
                break

        return True

    def _print_stats(self):
        """Print performance statistics for all modes."""
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE STATISTICS")
        logger.info("="*60)
        for mode, stats in self.stats.items():
            if stats["count"] > 0:
                logger.info(
                    f"  {mode:12} | Chunks: {stats['count']:8} | "
                    f"Avg time: {stats['avg_time']:6.2f}ms"
                )
        logger.info("="*60 + "\n")

    def _print_menu(self):
        """Print control menu."""
        logger.info("\n" + "=" * 70)
        logger.info("REAL-TIME VOICE CHANGER - CONTROLS")
        logger.info("=" * 70)
        logger.info("\n  EFFECTS:")
        logger.info("    1 → Passthrough (no effect, baseline)")
        logger.info("    2 → Echo       (y[n] = x[n] + 0.6*x[n-delay])")
        logger.info("    3 → Robot      (y[n] = |x[n]| + quantization)")
        logger.info("    4 → Pitch      (±5 semitones)")
        logger.info("\n  NOISE GATE (removes background noise):")
        logger.info("    g → Toggle noise gate ON/OFF")
        logger.info("    + → Increase threshold (less aggressive)")
        logger.info("    - → Decrease threshold (more aggressive)")
        logger.info("\n  OPTIONS:")
        logger.info("    v → Toggle visualization (real-time waveform)")
        logger.info("    d → Show performance stats")
        logger.info("    ? → Show this menu")
        logger.info("    q → Quit")
        logger.info("\n  STATUS:")
        gate_status = "ON" if self.pipeline.noise_gate_enabled else "OFF"
        logger.info(
            f"    Mode: {self.mode.upper()} | "
            f"Gate: {gate_status} (threshold: {self.pipeline.noise_gate_threshold:.3f}) | "
            f"Latency: ~%.1fms | Input: %s" % (
                self.audio_stream.latency_ms,
                "TEST SINE WAVE" if self.test_mode else "MICROPHONE"
            )
        )
        logger.info("=" * 70 + "\n")

    def _setup_visualization(self):
        """Setup matplotlib visualization window."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available - visualization disabled")
            self.visualize = False
            return

        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7))
            fig.suptitle("Real-Time Voice Changer - Waveform Analysis", fontsize=14)

            # Configure axes
            for ax in [ax1, ax2]:
                ax.set_ylim(-1.0, 1.0)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_ylabel("Amplitude", fontsize=10)

            ax1.set_title("Input Signal", fontsize=12, loc='left')
            ax2.set_title("Output Signal (Effect: %s)" % self.mode.upper(), fontsize=12, loc='left')
            ax2.set_xlabel("Time (samples)", fontsize=10)

            # Create line objects for efficient updating
            line1, = ax1.plot([], [], color="steelblue", linewidth=0.5, alpha=0.8)
            line2, = ax2.plot([], [], color="coral", linewidth=0.5, alpha=0.8)

            plt.tight_layout()

            def update_plot(frame):
                # Update input waveform
                if len(self.input_history) > 0:
                    x_data = np.arange(len(self.input_history))
                    line1.set_data(x_data, list(self.input_history))
                    ax1.set_xlim(0, max(MAX_HISTORY, len(self.input_history)))

                # Update output waveform
                if len(self.output_history) > 0:
                    x_data = np.arange(len(self.output_history))
                    line2.set_data(x_data, list(self.output_history))
                    ax2.set_xlim(0, max(MAX_HISTORY, len(self.output_history)))
                    # Update title with current mode
                    ax2.set_title("Output Signal (Effect: %s)" % self.mode.upper(), fontsize=12, loc='left')

                return line1, line2

            # Create animation (efficient line update, not full redraw)
            ani = FuncAnimation(
                fig, update_plot,
                interval=VIZ_UPDATE_INTERVAL,
                blit=True,  # Blit = only update changed regions (faster)
                cache_frame_data=False
            )

            plt.show()

        except Exception as e:
            logger.error(f"Visualization error: {e}")
            self.visualize = False

    def run(self):
        """Run the voice changer application main loop."""
        self.running = True

        # Set up processor (either test generator or microphone)
        if self.test_mode:
            # Use generated test signal
            def test_processor(dummy_audio):
                return self.test_generator.generate_sine(len(dummy_audio))

            self.audio_stream.set_processor(
                lambda x: self.process_audio(test_processor(x))
            )
        else:
            # Use actual microphone input
            self.audio_stream.set_processor(self.process_audio)

        try:
            # Start audio stream
            logger.info("Starting audio stream...")
            self.audio_stream.start()

            # Print menu
            self._print_menu()

            # Start keyboard input thread
            self.keyboard_thread = threading.Thread(target=self._read_keyboard, daemon=True)
            self.keyboard_thread.start()

            # Start visualization thread (if enabled)
            viz_thread = None
            if self.visualize and MATPLOTLIB_AVAILABLE:
                viz_thread = threading.Thread(target=self._setup_visualization, daemon=True)
                viz_thread.start()

            # Main loop
            while self.running:
                # Handle keyboard input (non-blocking)
                if not self._handle_input():
                    break

                time.sleep(0.01)  # Small sleep to prevent busy-waiting

        except KeyboardInterrupt:
            logger.info("\n⏹ Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            self.running = False
            self.audio_stream.stop()
            self._print_stats()
            logger.info("✓ Voice changer stopped")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    try:
        logger.info("="*70)
        logger.info("Real-Time Audio Signal Processing System")
        logger.info("="*70)
        logger.info(f"Test Mode: {TEST_MODE}")
        logger.info(f"Sample Rate: {SAMPLE_RATE} Hz")
        logger.info(f"Chunk Size: {CHUNK_SIZE} samples (~{CHUNK_SIZE/SAMPLE_RATE*1000:.1f}ms latency)")
        logger.info("="*70 + "\n")

        app = RealTimeVoiceChanger(
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            test_mode=TEST_MODE
        )
        app.run()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()

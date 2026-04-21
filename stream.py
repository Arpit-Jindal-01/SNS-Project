"""Real-time audio streaming engine with improved buffer handling.

BUFFER AND LATENCY MANAGEMENT:
- blocksize (chunk_size): Number of samples processed per callback
  * 1024 samples @ 44100 Hz = ~23ms latency (good balance)
  * Smaller = lower latency but more CPU overhead
  * Larger = higher latency but less CPU overhead
- Channel ordering: Input/output arrays are [samples, channels]
- Data copy: CRITICAL - we copy input data to prevent buffer corruption

PREVENTING AUDIO GLITCHES:
1. Copy input buffer immediately (avoid sounddevice reusing it)
2. Use appropriate dtype (float32 for audio processing)
3. Ensure output stays in [-1, 1] range (prevent clipping)
4. Handle underflow/overflow with checks and logging
5. Use latency="low" to minimize system buffer
"""

import numpy as np
import sounddevice as sd
import threading
import queue
from typing import Callable, Optional
import logging

# Configure logging (once per module)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class AudioStream:
    """Real-time audio input/output stream processor with buffer management."""

    def __init__(
        self,
        sample_rate=44100,
        chunk_size=1024,
        input_device=None,
        output_device=None,
        channels=1,
        verbose=False
    ):
        """Initialize audio stream.

        PARAMETERS:
        - sample_rate: Hz (default 44100 = CD quality, Nyquist limit 22050 Hz)
        - chunk_size: samples per callback (1024 @ 44100Hz = 23ms latency)
        - input_device: device index (None = system default microphone)
        - output_device: device index (None = system default speakers)
        - channels: audio channels (1 = mono, 2 = stereo)
        - verbose: enable frame-level debug logging

        Args:
            sample_rate: Sample rate in Hz (default 44100)
            chunk_size: Number of samples per chunk (default 1024 for ~23ms latency)
            input_device: Input device index (None = default)
            output_device: Output device index (None = default)
            channels: Number of audio channels (default 1 = mono)
            verbose: Enable detailed logging
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.input_device = input_device
        self.output_device = output_device
        self.verbose = verbose

        # Processing function
        self.process_func: Optional[Callable] = None

        # Stream state
        self.is_running = False
        self.stream = None

        # Latency calculation
        # latency_ms = samples / (sample_rate / 1000)
        self.latency_ms = (chunk_size / sample_rate) * 1000

        # Signal statistics for debugging
        self.frame_count = 0
        self.clipping_count = 0
        self.underflow_count = 0
        self.overflow_count = 0

    def set_processor(self, process_func: Callable):
        """Set the audio processing function.

        Args:
            process_func: Function that takes audio array and returns processed audio
                         Should maintain input dtype (float32) and stay in [-1, 1] range
        """
        self.process_func = process_func

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        """Real-time audio callback - processes chunk in audio thread.

        CRITICAL FOR REAL-TIME PERFORMANCE:
        - This runs in audio thread (high priority)
        - MUST complete before next chunk arrives
        - Cannot use print() (blocks thread) - use logging only
        - MUST NOT allocate large arrays
        - Should be under 1ms for 1024 samples @ 44100Hz

        Args:
            indata: Input buffer [frames, channels] - float32, [-1, 1] range
            outdata: Output buffer [frames, channels] - write results here
            frames: Number of samples in this chunk (usually chunk_size)
            time_info: Timing information (frame number, callback time)
            status: Stream status (underflow/overflow flags)
        """

        # CHECK FOR STREAM ISSUES
        if status:
            # Status flags indicate buffer problems
            if status.input_underflow:
                self.underflow_count += 1
                if self.verbose:
                    logger.warning(f"⚠ Input underflow (mic buffer too slow)")
            if status.output_underflow:
                self.underflow_count += 1
                if self.verbose:
                    logger.warning(f"⚠ Output underflow (processing too slow)")
            if status.input_overflow:
                self.overflow_count += 1
                if self.verbose:
                    logger.warning(f"⚠ Input overflow (mic data lost)")
            if status.output_overflow:
                self.overflow_count += 1
                if self.verbose:
                    logger.warning(f"⚠ Output overflow (output buffer full)")

        try:
            # STEP 1: EXTRACT INPUT
            # CRITICAL: Copy data immediately to avoid sounddevice reusing the buffer
            # indata shape: [frames, channels], we want mono (first channel)
            input_audio = indata[:, 0].copy().astype(np.float32)

            if self.verbose and self.frame_count % 100 == 0:
                # Log input statistics (every 100th frame to reduce spam)
                input_min = float(input_audio.min())
                input_max = float(input_audio.max())
                logger.debug(
                    f"Input | Shape: {input_audio.shape} | Range: [{input_min:.3f}, {input_max:.3f}]"
                )

            # STEP 2: PROCESS AUDIO
            if self.process_func:
                output_audio = self.process_func(input_audio)
            else:
                output_audio = input_audio

            # Ensure output is float32 (may have been converted by effects)
            if output_audio.dtype != np.float32:
                output_audio = output_audio.astype(np.float32)

            # STEP 3: CHECK FOR CLIPPING
            # Clipping = signal exceeds ±1.0 (causes harsh digital distortion)
            output_max = np.abs(output_audio).max()
            if output_max > 1.0:
                self.clipping_count += 1
                if self.verbose:
                    logger.warning(f"⚠ Clipping! Peak: {output_max:.3f} (should be ≤ 1.0)")

            # STEP 4: HARD CLIP TO PREVENT DAC OVERFLOW
            # Final safety: ensure values stay in valid range
            # This should rarely trigger if effects normalize properly
            output_audio = np.clip(output_audio, -1.0, 1.0)

            # STEP 5: WRITE OUTPUT
            # Write to first channel of output buffer
            outdata[:, 0] = output_audio

            if self.verbose and self.frame_count % 100 == 0:
                # Log output statistics
                output_min = float(output_audio.min())
                output_max = float(output_audio.max())
                logger.debug(
                    f"Output | Shape: {output_audio.shape} | Range: [{output_min:.3f}, {output_max:.3f}]"
                )

        except Exception as e:
            # Log error but don't crash (callback must not raise)
            logger.error(f"Callback error: {e}")
            # Output silence if processing fails
            outdata[:, 0] = 0.0

        finally:
            # Always increment frame counter
            self.frame_count += 1

    def start(self):
        """Start the audio stream and begin processing."""
        if self.is_running:
            logger.warning("Stream already running")
            return

        try:
            # Create stream with optimized settings
            self.stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=self.channels,
                device=(self.input_device, self.output_device),
                callback=self._audio_callback,
                latency="low",  # Minimize system buffer latency
                dtype=np.float32  # Use float32 throughout
            )

            # Start streaming
            self.stream.start()
            self.is_running = True

            logger.info(
                f"✓ Stream started | Rate: {self.sample_rate} Hz | "
                f"Chunk: {self.chunk_size} | Latency: ~{self.latency_ms:.1f}ms"
            )

        except Exception as e:
            logger.error(f"Error starting audio stream: {e}")
            raise

    def stop(self):
        """Stop the audio stream and cleanup resources."""
        if not self.is_running:
            return

        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
            self.is_running = False

            # Print statistics on stop
            logger.info(
                f"✓ Stream stopped | "
                f"Frames: {self.frame_count:,} | "
                f"Clipping events: {self.clipping_count} | "
                f"Underflow: {self.underflow_count} | "
                f"Overflow: {self.overflow_count}"
            )

        except Exception as e:
            logger.error(f"Error stopping stream: {e}")

    def list_devices(self):
        """Print available audio devices for device selection."""
        logger.info("Available audio devices:")
        print(sd.query_devices())

    def __enter__(self):
        """Context manager entry - start stream."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop stream."""
        self.stop()

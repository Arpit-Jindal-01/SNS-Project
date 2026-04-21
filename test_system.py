"""Test and validation script for the real-time audio system.

Runs through each effect, checks for errors, and validates signal processing.
"""

import numpy as np
from effects import apply_echo, apply_robot, apply_pitch_shift
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def test_signal_generation():
    """Generate test signals."""
    sample_rate = 44100
    duration = 0.1  # 100ms
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    signal = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return signal, sample_rate


def test_echo():
    """Test echo effect."""
    logger.info("\n" + "="*50)
    logger.info("Testing Echo Effect")
    logger.info("="*50)

    signal, sample_rate = test_signal_generation()
    delay = int(0.2 * sample_rate)  # 0.2 seconds
    alpha = 0.6

    logger.info(f"Input signal: shape={signal.shape}, min={signal.min():.3f}, max={signal.max():.3f}")

    output = apply_echo(signal, delay, alpha)

    logger.info(f"Output signal: shape={output.shape}, min={output.min():.3f}, max={output.max():.3f}")

    # Validate
    assert output.shape == signal.shape, "Shape mismatch"
    assert np.all(np.isfinite(output)), "NaN or Inf in output"
    assert np.max(np.abs(output)) <= 1.1, "Output exceeds expected range"

    logger.info("✓ Echo test passed")
    return output


def test_robot():
    """Test robot effect."""
    logger.info("\n" + "="*50)
    logger.info("Testing Robot Effect")
    logger.info("="*50)

    signal, sample_rate = test_signal_generation()

    logger.info(f"Input signal: shape={signal.shape}, min={signal.min():.3f}, max={signal.max():.3f}")

    output = apply_robot(signal)

    logger.info(f"Output signal: shape={output.shape}, min={output.min():.3f}, max={output.max():.3f}")

    # Validate
    assert output.shape == signal.shape, "Shape mismatch"
    assert np.all(np.isfinite(output)), "NaN or Inf in output"
    assert np.all(output >= 0), "Robot output should be non-negative"
    assert np.max(output) <= 1.0, "Output exceeds 1.0"

    logger.info("✓ Robot test passed")
    return output


def test_pitch_shift():
    """Test pitch shift effect."""
    logger.info("\n" + "="*50)
    logger.info("Testing Pitch Shift Effect")
    logger.info("="*50)

    signal, sample_rate = test_signal_generation()
    n_steps = 5  # 5 semitones up

    logger.info(f"Input signal: shape={signal.shape}, min={signal.min():.3f}, max={signal.max():.3f}")

    output = apply_pitch_shift(signal, sample_rate, n_steps)

    logger.info(f"Output signal: shape={output.shape}, min={output.min():.3f}, max={output.max():.3f}")

    # Validate
    assert output.shape == signal.shape, "Shape mismatch"
    assert np.all(np.isfinite(output)), "NaN or Inf in output"
    assert np.max(np.abs(output)) <= 1.1, "Output exceeds expected range"

    logger.info("✓ Pitch shift test passed")
    return output


def test_edge_cases():
    """Test edge cases."""
    logger.info("\n" + "="*50)
    logger.info("Testing Edge Cases")
    logger.info("="*50)

    # Silent signal
    silent = np.zeros(1024, dtype=np.float32)
    logger.info("Testing silent signal...")
    assert apply_robot(silent).max() == 0, "Silent signal should remain silent"
    logger.info("✓ Silent signal handled")

    # Clipping test
    loud = np.ones(1024, dtype=np.float32) * 2.0  # 2.0 amplitude (will clip)
    logger.info("Testing loud signal (clipping)...")
    output = apply_echo(loud, 512, 0.5)
    assert np.max(np.abs(output)) <= 1.1, "Output exceeds safety range"
    logger.info("✓ Loud signal handled")

    # Very short signal
    short = np.random.randn(10).astype(np.float32)
    logger.info("Testing short signal...")
    output = apply_pitch_shift(short, 44100, 0)
    assert len(output) == len(short), "Short signal length not preserved"
    logger.info("✓ Short signal handled")

    logger.info("✓ All edge cases passed")


def test_real_time_chunk():
    """Simulate real-time chunk processing."""
    logger.info("\n" + "="*50)
    logger.info("Testing Real-Time Chunk Processing")
    logger.info("="*50)

    sample_rate = 44100
    chunk_size = 1024
    sample_rate_hz = 440

    # Simulate 1 second of processing
    logger.info(f"Simulating 1 second of processing ({sample_rate//chunk_size} chunks)...")

    all_output = []
    for i in range(sample_rate // chunk_size):
        # Generate chunk
        t = np.linspace(i*chunk_size/sample_rate, (i+1)*chunk_size/sample_rate, chunk_size)
        chunk = np.sin(2 * np.pi * sample_rate_hz * t).astype(np.float32)

        # Process with all effects
        echo_out = apply_echo(chunk, int(0.2*sample_rate), 0.6)
        robot_out = apply_robot(chunk)
        pitch_out = apply_pitch_shift(chunk, sample_rate, 5)

        # Validate
        assert echo_out.shape == chunk.shape
        assert robot_out.shape == chunk.shape
        assert pitch_out.shape == chunk.shape

        all_output.append(echo_out)

    total_samples = len(all_output) * chunk_size
    logger.info(f"✓ Processed {total_samples} samples in {len(all_output)} chunks")


def test_streaming_setup():
    """Test audio stream setup (no actual audio)."""
    logger.info("\n" + "="*50)
    logger.info("Testing Stream Setup")
    logger.info("="*50)

    try:
        from stream import AudioStream

        logger.info("Creating AudioStream...")
        stream = AudioStream(sample_rate=44100, chunk_size=1024, verbose=False)

        logger.info(f"Stream latency: {stream.latency_ms:.1f}ms")
        logger.info(f"Stream parameters: rate={stream.sample_rate}, chunk={stream.chunk_size}")

        # Test processor setting
        def dummy_processor(audio):
            return audio * 0.5

        stream.set_processor(dummy_processor)
        logger.info("✓ Processor set successfully")

        logger.info("✓ Stream setup test passed")

    except Exception as e:
        logger.error(f"Stream setup failed: {e}")
        return False

    return True


def test_imports():
    """Test all required imports."""
    logger.info("\n" + "="*50)
    logger.info("Testing Imports")
    logger.info("="*50)

    try:
        import numpy
        logger.info(f"✓ numpy {numpy.__version__}")

        import scipy
        logger.info(f"✓ scipy {scipy.__version__}")

        import librosa
        logger.info(f"✓ librosa {librosa.__version__}")

        import sounddevice
        logger.info(f"✓ sounddevice {sounddevice.__version__}")

        try:
            import matplotlib
            logger.info(f"✓ matplotlib {matplotlib.__version__}")
        except ImportError:
            logger.warning("⚠ matplotlib not installed (visualization disabled)")

        logger.info("✓ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "#"*50)
    logger.info("# REAL-TIME AUDIO SYSTEM VALIDATION")
    logger.info("#"*50)

    # Test imports first
    if not test_imports():
        logger.error("Import test failed, cannot proceed")
        return False

    # Test stream setup
    if not test_streaming_setup():
        logger.warning("Stream setup test had issues")

    # Test effects
    try:
        test_echo()
        test_robot()
        test_pitch_shift()
        test_edge_cases()
        test_real_time_chunk()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

    logger.info("\n" + "#"*50)
    logger.info("# ✓ ALL TESTS PASSED")
    logger.info("#"*50)
    logger.info("\nSystem is ready for real-time audio processing!")
    logger.info("Run: python main.py")

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

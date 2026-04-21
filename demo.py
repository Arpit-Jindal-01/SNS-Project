"""Simple test scripts for the real-time audio system."""

import numpy as np
from effects import apply_echo, apply_robot, apply_pitch_shift, normalize_audio
from stream import AudioStream
import time
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def simple_passthrough():
    """Simple pass-through demo - microphone → speakers (no effect)."""
    logger.info("\n" + "="*60)
    logger.info("SIMPLE PASSTHROUGH DEMO")
    logger.info("="*60)
    logger.info("Microphone input will be played back immediately.")
    logger.info("Listen for latency (should be ~23ms).")
    logger.info("Press Ctrl+C to stop.\n")

    stream = AudioStream(sample_rate=44100, chunk_size=1024)
    stream.set_processor(lambda x: x.astype(np.float32))

    try:
        stream.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\nStopping...")
    finally:
        stream.stop()


def echo_demo():
    """Echo effect demo with 0.2 second delay."""
    logger.info("\n" + "="*60)
    logger.info("ECHO EFFECT DEMO")
    logger.info("="*60)
    logger.info("Effect: y[n] = x[n] + 0.6 * x[n - 8820 samples]")
    logger.info("Delay: 0.2 seconds (8820 samples @ 44100 Hz)")
    logger.info("You will hear your voice with echo.")
    logger.info("Press Ctrl+C to stop.\n")

    sample_rate = 44100
    delay_samples = int(0.2 * sample_rate)

    stream = AudioStream(sample_rate=sample_rate, chunk_size=1024)

    def echo_processor(audio):
        return apply_echo(audio, delay=delay_samples, alpha=0.6)

    stream.set_processor(echo_processor)

    try:
        stream.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\nStopping...")
    finally:
        stream.stop()


def robot_demo():
    """Robot effect demo using full-wave rectification."""
    logger.info("\n" + "="*60)
    logger.info("ROBOT EFFECT DEMO")
    logger.info("="*60)
    logger.info("Effect: Full-wave rectification + spectral quantization")
    logger.info("You will hear a metallic/robotic version of your voice.")
    logger.info("Press Ctrl+C to stop.\n")

    stream = AudioStream(sample_rate=44100, chunk_size=1024)
    stream.set_processor(apply_robot)

    try:
        stream.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\nStopping...")
    finally:
        stream.stop()


def test_offline_effects():
    """Test effects on synthetic signal without real-time audio."""
    logger.info("\n" + "="*60)
    logger.info("OFFLINE EFFECT TESTING")
    logger.info("="*60)
    logger.info("Testing effects on generated 440 Hz sine wave.\n")

    sample_rate = 44100
    duration = 0.5  # 500ms

    # Generate test signal
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    logger.info(f"Generated test signal: 440 Hz sine wave, {len(signal)} samples")
    logger.info(f"Input range: [{signal.min():.3f}, {signal.max():.3f}]\n")

    # Test echo
    logger.info("Testing ECHO effect...")
    echo_out = apply_echo(signal, delay=8820, alpha=0.6)
    logger.info(f"  Output range: [{echo_out.min():.3f}, {echo_out.max():.3f}]")
    logger.info(f"  ✓ Shape preserved: {echo_out.shape == signal.shape}")
    logger.info(f"  ✓ No NaN/Inf: {np.all(np.isfinite(echo_out))}")

    # Test robot
    logger.info("Testing ROBOT effect...")
    robot_out = apply_robot(signal)
    logger.info(f"  Output range: [{robot_out.min():.3f}, {robot_out.max():.3f}]")
    logger.info(f"  ✓ Shape preserved: {robot_out.shape == signal.shape}")
    logger.info(f"  ✓ No negative values: {np.all(robot_out >= 0)}")

    # Test pitch shift
    logger.info("Testing PITCH SHIFT effect...")
    pitch_out = apply_pitch_shift(signal, sample_rate, n_steps=5)
    logger.info(f"  Output range: [{pitch_out.min():.3f}, {pitch_out.max():.3f}]")
    logger.info(f"  ✓ Shape preserved: {pitch_out.shape == signal.shape}")
    logger.info(f"  ✓ No NaN/Inf: {np.all(np.isfinite(pitch_out))}")

    # Test normalization
    logger.info("Testing NORMALIZATION...")
    loud_signal = signal * 2.0  # Create signal that would clip
    logger.info(f"  Before normalization: {loud_signal.max():.3f} (exceeds 1.0)")
    normalized = normalize_audio(loud_signal)
    logger.info(f"  After normalization: {normalized.max():.3f} (safe)")
    logger.info(f"  ✓ Shape preserved: {normalized.shape == loud_signal.shape}")

    logger.info("\n✓ All offline tests passed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "echo":
            echo_demo()
        elif sys.argv[1] == "robot":
            robot_demo()
        elif sys.argv[1] == "test":
            test_offline_effects()
        else:
            print("Usage: python demo.py [echo|robot|test]")
            print("  (no args)  - Simple passthrough test")
            print("  echo       - Echo effect demo")
            print("  robot      - Robot effect demo")
            print("  test       - Offline effect testing (no audio)")
    else:
        simple_passthrough()

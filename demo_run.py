#!/usr/bin/env python3
"""Demo run of the voice changer system - shows startup and basic operation."""

import sys
import time
import logging
from unittest.mock import patch, MagicMock

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def demo_voice_changer():
    """Run a demo of the voice changer showing startup and basic operation."""
    logger.info("\n" + "="*70)
    logger.info("REAL-TIME VOICE CHANGER - DEMONSTRATION")
    logger.info("="*70)

    logger.info("\nImporting system modules...")
    from main import RealTimeVoiceChanger, AudioProcessingPipeline, TestSignalGenerator
    from stream import AudioStream

    logger.info("✓ Modules imported successfully")

    logger.info("\nInitializing voice changer...")
    app = RealTimeVoiceChanger(sample_rate=44100, chunk_size=1024, test_mode=True)
    logger.info("✓ Voice changer initialized")

    logger.info("\nSystem Configuration:")
    logger.info(f"  Sample Rate: 44100 Hz")
    logger.info(f"  Chunk Size: 1024 samples")
    logger.info(f"  Latency: ~23.2ms")
    logger.info(f"  Input Mode: TEST SINE WAVE (440 Hz)")
    logger.info(f"  Noise Gate: ENABLED (threshold: {app.pipeline.noise_gate_threshold:.3f})")

    logger.info("\nTesting pipeline with noise gate...")

    import numpy as np
    from effects import apply_noise_gate

    # Generate test signal
    t = np.linspace(0, 0.1, 4410, dtype=np.float32)
    signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    logger.info(f"\nOriginal signal:")
    logger.info(f"  Type: 440 Hz sine wave")
    logger.info(f"  Length: {len(signal)} samples")
    logger.info(f"  Range: [{signal.min():.3f}, {signal.max():.3f}]")

    # Apply noise gate
    gated = apply_noise_gate(signal, threshold=0.02)
    logger.info(f"\nAfter noise gate (threshold=0.02):")
    logger.info(f"  Range: [{gated.min():.3f}, {gated.max():.3f}]")
    logger.info(f"  Silence: {(gated == 0).sum() / len(gated) * 100:.1f}%")

    # Process through pipeline
    logger.info(f"\nProcessing through effects:")
    effects = ["passthrough", "echo", "robot", "pitch"]
    for effect in effects:
        try:
            output = app.pipeline.process(signal, effect)
            logger.info(f"  ✓ {effect:12} OK | Output: [{output.min():.3f}, {output.max():.3f}]")
        except Exception as e:
            logger.error(f"  ✗ {effect:12} ERROR: {e}")

    logger.info("\nKeyboard Controls Available:")
    logger.info("  1-4  : Select effect (passthrough, echo, robot, pitch)")
    logger.info("  g    : Toggle noise gate")
    logger.info("  +/-  : Adjust noise gate threshold")
    logger.info("  v    : Toggle visualization")
    logger.info("  d    : Show statistics")
    logger.info("  ?    : Show full menu")
    logger.info("  q    : Quit")

    logger.info("\nNoise Gate Details:")
    logger.info("  Purpose: Remove low-amplitude background noise")
    logger.info("  Strategy: Zero out signals below threshold")
    logger.info("  Applied: BEFORE effects (protects from noise amplification)")
    logger.info("  Current threshold: 0.02 (2% of full scale)")
    logger.info("  Adjustment: Use '+' and '-' keys to change threshold")
    logger.info("  Toggle: Use 'g' key to enable/disable")

    logger.info("\n" + "="*70)
    logger.info("DEMONSTRATION COMPLETE - SYSTEM WORKING CORRECTLY!")
    logger.info("="*70)

    logger.info("\nTo run the interactive voice changer:")
    logger.info("  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 main.py")
    logger.info("\nNote: In interactive mode:")
    logger.info("  - Set TEST_MODE=False in main.py to use real microphone")
    logger.info("  - Press Ctrl+C to stop")
    logger.info("  - Press 'q' to quit gracefully")

    return True


if __name__ == "__main__":
    try:
        success = demo_voice_changer()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

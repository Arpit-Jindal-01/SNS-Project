"""Audio effects processing module with normalization.

This module contains core signal processing functions for real-time audio effects,
with emphasis on stability and preventing digital artifacts like clipping.

SAMPLING FUNDAMENTALS:
- Nyquist Theorem: Maximum frequency = sample_rate / 2
- At 44100 Hz: Can represent frequencies up to 22,050 Hz (human hearing limit ~20 kHz)
- Each sample = amplitude (-1.0 to 1.0 in float32, or -32768 to 32767 in int16)

LINEAR vs NON-LINEAR PROCESSING:
- Linear: Output is proportional to input (e.g., gain scaling, delay)
- Non-Linear: Relationship is curved (e.g., rectification, soft clipping)
  This creates harmonics and can cause unwanted artifacts if not managed

WHY NORMALIZATION IS CRITICAL:
- Digital audio must stay in [-1, 1] range (float) or [-32768, 32767] (int16)
- Values exceeding this cause clipping: hard cutoff that distorts signal
- Multiple effects can combine to exceed 1.0 (e.g., echo adds to original)
- Normalization prevents clipping while maintaining audio quality
"""

import numpy as np
import librosa


def apply_noise_gate(signal, threshold=0.02):
    """Apply noise gate: zero out signals below threshold.

    NOISE GATE PURPOSE:
    - Removes low-level background noise (room hum, fan noise, etc.)
    - Only passes signals stronger than threshold
    - Simple but effective noise reduction
    - Applied BEFORE effects to reduce processing on noise

    FORMULA:
    - If |x[n]| < threshold: y[n] = 0 (silence)
    - If |x[n]| >= threshold: y[n] = x[n] (pass through unchanged)

    WHY THIS WORKS:
    - Background noise is typically low-amplitude
    - Voice/music signals exceed noise floor
    - Prevents effects from amplifying quiet background noise

    Args:
        signal: numpy array of audio samples
        threshold: amplitude threshold (0.0-1.0, default 0.02)
                  Example: 0.02 = 2% of full scale

    Returns:
        Signal with noise gated, same shape as input

    Example:
        >>> signal = np.array([0.01, 0.05, 0.5, 0.02])  # Mix of noise and signal
        >>> gated = apply_noise_gate(signal, threshold=0.03)
        >>> gated  # [0.0, 0.05, 0.5, 0.0]  (noise zeroed)
    """
    # Create output array
    output = np.array(signal, copy=True, dtype=np.float32)

    # Apply gate: zero out samples below threshold
    # This is a VECTORIZED operation (efficient, no Python loop)
    output[np.abs(output) < threshold] = 0.0

    return output.astype(np.float32)


def normalize_audio(signal, target_peak=0.95, epsilon=1e-8):
    """Normalize audio signal to prevent clipping while maintaining dynamics.

    NORMALIZATION PROCESS:
    1. Find peak (max absolute value) in signal
    2. Scale signal so peak = target_peak (e.g., 0.95)
    3. Prevents digital clipping (values > 1.0)
    4. Maintains relative amplitude differences

    Args:
        signal: numpy array of audio samples (float32)
        target_peak: Peak amplitude after normalization (0.0-1.0, default 0.95)
        epsilon: Minimum value to avoid division by zero (default 1e-8)

    Returns:
        Normalized audio array, same shape as input, values in [-1, 1]

    Example:
        >>> signal = np.array([0.5, 1.2, -0.8])  # Peak = 1.2 (will clip!)
        >>> normalized = normalize_audio(signal, target_peak=0.95)
        >>> np.max(np.abs(normalized))  # Will be 0.95
    """
    # Find current peak (maximum absolute value)
    peak = np.max(np.abs(signal))

    # Only normalize if signal exceeds target peak
    if peak > target_peak:
        # Scale signal to target peak
        output = signal * (target_peak / (peak + epsilon))
    else:
        # Signal is already safe
        output = signal.copy()

    # Ensure dtype is float32 (32-bit floating point)
    # float32 is standard for audio (good precision, memory efficient)
    output = output.astype(np.float32)

    # Final safety clip (shouldn't need this if normalization worked)
    output = np.clip(output, -1.0, 1.0)

    return output


def apply_echo(signal, delay, alpha):
    """Apply echo/delay effect: y[n] = x[n] + alpha * x[n - delay].

    EFFECT EXPLANATION (LINEAR PROCESSING):
    - Echo is a LINEAR effect: output proportional to input
    - Creates a copy of signal delayed by N samples
    - Mixes delayed signal back with original
    - Multiple echoes can accumulate and exceed 1.0!

    FORMULA:
    - y[n] = x[n] + α * x[n-delay]
    - When n < delay: y[n] = x[n] (no delayed copy available yet)
    - When n ≥ delay: y[n] = x[n] + α * x[n-delay] (original + delayed)

    WHY MULTIPLY BY ALPHA:
    - α = feedback strength (0.0 = no echo, 1.0 = full strength)
    - Without α, echoes would grow unbounded
    - Typical α = 0.6 keeps echoes audible but controlled

    Args:
        signal: numpy array of audio samples
        delay: number of samples to delay (integer)
        alpha: echo strength factor (0.0-1.0, higher = louder echoes)

    Returns:
        Echo-processed signal, normalized to prevent clipping
    """
    # Ensure delay is integer (can't delay by fractional samples)
    delay = int(np.clip(delay, 0, len(signal)))

    # VECTORIZED IMPLEMENTATION (efficient, no Python loops)
    # Create array of zeros same shape as input
    output = np.zeros_like(signal, dtype=np.float32)

    # Add original signal
    output[:] = signal

    # Add delayed signal (where available)
    if delay > 0:
        # This is equivalent to:
        # for n in range(len(signal)):
        #     if n - delay >= 0:
        #         output[n] += alpha * signal[n - delay]
        # But using numpy: output[delay:] += alpha * signal[:-delay]
        output[delay:] += alpha * signal[:-delay]

    # Normalize to prevent clipping from accumulated echoes
    return normalize_audio(output, target_peak=0.95)


def apply_robot(signal, num_bands=8):
    """Apply robot/vocoder effect using full-wave rectification and quantization.

    EFFECT EXPLANATION (NON-LINEAR PROCESSING):
    - Robot is a NON-LINEAR effect: output doesn't scale proportionally with input
    - Two components:
      1. Full-wave rectification: y[n] = |x[n]| (all negative → positive)
      2. Spectral quantization: Group frequencies into bands
    - Creates metallic, robotic sound by emphasizing pitch while removing noise

    RECTIFICATION:
    - Takes absolute value of each sample
    - Negative values → positive (removes phase information)
    - This is non-linear: -0.5 and +0.5 both → +0.5
    - Creates odd-order harmonics (adds metallic character)

    SPECTRAL QUANTIZATION:
    - Groups frequencies into N bands
    - Averages amplitude within each band
    - Creates quantized spectrum effect

    Args:
        signal: numpy array of audio samples
        num_bands: number of frequency bands (higher = more detail, default 8)

    Returns:
        Robot-effect signal, normalized to prevent clipping
    """
    # Full-wave rectification: y[n] = |x[n]|
    rectified = np.abs(signal)

    # Spectral analysis using STFT (Short-Time Fourier Transform)
    # FFT = Fast Fourier Transform, converts time-domain → frequency-domain
    try:
        # Perform STFT to get frequency content
        D = librosa.stft(rectified, n_fft=2048, hop_length=512)
        mag = np.abs(D)  # Magnitude spectrum
        phase = np.angle(D)  # Phase spectrum (preserve for reconstruction)

        # Quantize frequency bands
        # Group magnitude spectrum into N bands and average each
        for freq_bin in range(mag.shape[0]):
            # Determine which band this frequency belongs to
            band_idx = min(
                int(freq_bin * num_bands / mag.shape[0]),
                num_bands - 1
            )

            # Calculate band boundaries
            band_size = mag.shape[0] // num_bands
            band_start = band_idx * band_size
            band_end = min(band_start + band_size, mag.shape[0])

            # Average magnitude in this band
            if band_end > band_start:
                avg_magnitude = np.mean(mag[band_start:band_end, :])
                mag[freq_bin, :] = avg_magnitude

        # Reconstruct signal: ISTFT (Inverse STFT)
        # Combine magnitude and phase: magnitude * e^(i*phase)
        D_processed = mag * np.exp(1j * phase)
        output = librosa.istft(D_processed, hop_length=512)

        # Match output length to input
        if len(output) != len(signal):
            if len(output) > len(signal):
                output = output[:len(signal)]
            else:
                output = np.pad(output, (0, len(signal) - len(output)))

    except Exception as e:
        # Fall back to simple rectification if STFT fails
        print(f"Robot effect warning: {e}, using simple rectification")
        output = rectified

    # Normalize output (rectified signals often need normalization)
    return normalize_audio(output, target_peak=0.95)


def apply_pitch_shift(signal, sample_rate, n_steps):
    """Apply pitch shifting using phase vocoder algorithm.

    EFFECT EXPLANATION (NON-LINEAR, TIME-DOMAIN MANIPULATION):
    - Phase Vocoder algorithm (from librosa/STFT):
      1. Convert to frequency domain (STFT)
      2. Scale frequency axis by 2^(n_steps/12)
      3. Convert back to time domain (ISTFT)
    - Preserves tempo but changes pitch (unlike time-stretching)

    PITCH FORMULA:
    - New frequency = Original frequency * 2^(n_steps/12)
    - Each semitone = 2^(1/12) ≈ 1.0594
    - Example: +12 semitones = 2x frequency (one octave higher)
    - Example: -12 semitones = 0.5x frequency (one octave lower)

    WHY THIS WORKS:
    - Audio is periodic (repeating waveform)
    - Shifting phase progression → changes pitch while keeping timing same

    Args:
        signal: numpy array of audio samples (must be reasonably short for real-time)
        sample_rate: sample rate in Hz (e.g., 44100)
        n_steps: semitones to shift (positive=higher, negative=lower)

    Returns:
        Pitch-shifted signal, normalized, length-matched to input
    """
    # If no pitch shift requested, return unchanged
    if n_steps == 0:
        return signal.astype(np.float32)

    try:
        # Validate inputs
        if len(signal) < 512:
            # Signal too short for reliable pitch shifting
            print(f"Warning: signal too short for pitch shift ({len(signal)} samples)")
            return signal.astype(np.float32)

        # Use librosa's phase vocoder
        # n_steps = semitones to shift
        # n_fft = FFT size (larger = more accurate but slower)
        shifted = librosa.effects.pitch_shift(
            signal,
            sr=sample_rate,
            n_steps=int(n_steps),
            n_fft=2048  # Good balance for real-time: 2048 samples ≈ 46ms @ 44100Hz
        )

        # Match output length to input (librosa may return different length)
        if len(shifted) != len(signal):
            if len(shifted) > len(signal):
                # Trim excess
                shifted = shifted[:len(signal)]
            else:
                # Pad with zeros (silence at end)
                shifted = np.pad(shifted, (0, len(signal) - len(shifted)))

        # Return normalized (pitch shifting can cause peaks)
        return normalize_audio(shifted, target_peak=0.95)

    except Exception as e:
        print(f"Pitch shift error: {e}")
        # Return input unchanged if pitch shift fails
        return signal.astype(np.float32)


def apply_passthrough(signal):
    """Pass-through (identity) effect - no processing.

    Used for:
    - Testing baseline latency
    - Verifying audio pipeline works
    - Comparing effect performance
    """
    return signal.astype(np.float32)


class PassThroughEffect:
    """Pass-through effect class (for compatibility with old code)."""

    def process(self, audio):
        """Return audio unchanged."""
        return apply_passthrough(audio)

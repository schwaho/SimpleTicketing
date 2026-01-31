"""
Audio signal generation utilities for piezo-style notification sounds.

This module provides functions to synthesize short, click-minimized
piezo beeps commonly used for scanner or embedded notification sounds.
It includes waveform generation, envelope shaping, DC offset correction,
click detection, filtering, silence generation, and MP3 export.

Notes:
    - The module assumes a global sampling rate constant `FS`.
    - All signals are mono and represented as NumPy arrays.
    - Designed for offline sound generation rather than real-time audio.
"""

import numpy as np
from scipy.io.wavfile import write
from scipy.signal import butter, filtfilt
from pydub import AudioSegment  # type: ignore[import-untyped]
from numpy.typing import NDArray
import matplotlib.pyplot as plt

FS = 44100  # Sample rate


def optimize_zero_dc(
    wave: np.ndarray, attack: int, release: int, alpha: float = 1.0, beta: float = 1.0
) -> NDArray[np.floating]:
    """
    Optimizes DC offset and edge behavior of an audio signal.

    The function applies a weighted combination of a DC shift and a
    global scaling factor to reduce DC offset in the steady-state
    region and move the start and end samples closer to zero.
    This helps to avoid clicks and discontinuities.

    Args:
        wave (np.ndarray): Audio signal waveform (1D array).
        attack (int): Number of samples to exclude at the start
            from DC estimation.
        release (int): Number of samples to exclude at the end
            from DC estimation.
        alpha (float, optional): Weight controlling the influence
            of edge (zero-crossing) optimization. Defaults to 1.0.
        beta (float, optional): Weight controlling the influence
            of DC offset removal. Defaults to 1.0.

    Returns:
        np.ndarray: Optimized waveform with reduced DC offset and
        improved start/end proximity to zero.

    Notes:
        - A higher `beta` emphasizes DC offset correction.
        - A higher `alpha` emphasizes reducing start/end deviations.
        - The DC offset is estimated from the signal excluding
          attack and release regions.
    """

    # Initial start and end sample values
    s0 = wave[0]
    e0 = wave[-1]

    # Middle region used for DC estimation
    mid_wave = wave[attack:-release]
    dc0 = np.mean(mid_wave)

    # DC shift: remove mean value, weighted by beta
    shift = -(beta / (alpha + beta)) * dc0

    # Scale: small global adjustment to move edges closer to zero
    scale = 1.0 - alpha / (alpha + beta) * ((s0 + e0) / 2)

    print(f"DC shift: {shift}")
    print(f"Scale factor: {scale}")

    wave_opt = wave * scale + shift
    return wave_opt


def lowpass(signal: np.ndarray, cutoff: float, fs: int, order: int = 4) -> np.ndarray:
    """
    Apply a zero-phase low-pass Butterworth filter to a signal.

    The filter is designed using a digital Butterworth prototype and
    applied with forward-backward filtering to avoid phase distortion.

    Args:
        signal (np.ndarray): Input signal to be filtered (1D array).
        cutoff (float): Cutoff frequency of the low-pass filter in Hz.
        fs (int): Sampling rate of the signal in Hz.
        order (int, optional): Order of the Butterworth filter.
            Higher values result in a steeper roll-off.
            Defaults to 4.

    Returns:
        np.ndarray: Low-pass filtered signal with zero phase shift.

    Notes:
        - The cutoff frequency is normalized by the Nyquist frequency.
        - `filtfilt` is used to ensure zero-phase filtering.
        - The signal length must be sufficient for the chosen filter order.
    """

    # Nyquist frequency
    nyq = 0.5 * fs

    # Normalized cutoff frequency (0 < normal_cutoff < 1)
    normal_cutoff = cutoff / nyq

    # Design Butterworth low-pass filter
    b, a = butter(order, normal_cutoff, btype="low", analog=False)

    # Apply zero-phase forward-backward filtering
    return filtfilt(b, a, signal)


def piezo_beep(
    freq: float,
    duration: float,
    attack_ms: int = 10,
    release_ms: int = 40,
    cutoff: float = 4000,
) -> NDArray[np.floating]:
    """
    Generate a smoothed piezo-style beep signal with click reduction.

    The signal is constructed as a band-limited triangle waveform with
    an attack/release envelope, DC offset optimization, and optional
    diagnostic plotting for start and end regions.

    Args:
        freq (float): Fundamental frequency of the beep in Hz.
        duration (float): Signal duration in seconds.
        attack_ms (int, optional): Attack time in milliseconds.
            Defaults to 8.
        release_ms (int, optional): Release time in milliseconds.
            Defaults to 40.
        cutoff (float, optional): Low-pass filter cutoff frequency in Hz
            used to smooth the waveform. Defaults to 4000.

    Returns:
        np.ndarray: Generated beep waveform.

    Notes:
        - The signal length is quantized to an integer number of periods
          to ensure zero-crossing alignment.
        - A triangle waveform is generated and smoothed using a low-pass
          filter to reduce high-frequency components.
        - An amplitude envelope is applied to avoid abrupt transitions.
        - DC offset and edge behavior are optimized to reduce clicks.
        - Diagnostic plots and click detection are shown for debugging.
    """

    # Compute signal length aligned to an integer number of periods
    samples_per_period = FS / freq
    n_periods = int(FS * duration / samples_per_period)
    num_samples = int(n_periods * samples_per_period)

    # Time axis
    t = np.arange(num_samples) / FS

    # Generate triangle waveform and smooth it
    wave = 0.8 * (2 * np.arcsin(np.sin(2 * np.pi * freq * t)) / np.pi)
    wave = lowpass(wave, cutoff=cutoff, fs=FS)

    # hard clipping to suppress remaining peaks
    # wave = np.clip(wave, -0.9, 0.9)

    # Create amplitude envelope
    envelope = np.ones_like(wave)
    attack = int(attack_ms / 1000 * FS)
    release = int(release_ms / 1000 * FS)

    envelope[:attack] = np.linspace(0, 1, attack, endpoint=False)
    envelope[-release:] = np.linspace(1, 0, release, endpoint=True)

    wave *= envelope

    wave = optimize_zero_dc(wave, attack, release)

    return wave


def silence(duration: float) -> NDArray[np.floating]:
    """
    Generate a silent audio signal of a given duration.

    Args:
        duration (float): Length of the silent signal in seconds.

    Returns:
        np.ndarray: Array of zeros representing silence.

    Notes:
        - The number of samples is determined using the global
          sampling rate `FS`.
    """
    return np.zeros(int(duration * FS))


def export_mp3(name: str, signal: np.ndarray, bitrate: str = "192k") -> None:
    """
    Export an audio signal as an MP3 file using a temporary WAV file.

    The signal is first written as a 16-bit PCM WAV file and then
    converted to MP3 format using pydub.

    Args:
        name (str): Base filename (without extension) for the output files.
        signal (np.ndarray): Audio signal waveform (1D array, mono).
        bitrate (str, optional): Target MP3 bitrate (e.g., "128k", "192k").
            Defaults to "192k".

    Notes:
        - The signal is assumed to be normalized to the range [-1.0, 1.0].
        - A temporary WAV file is created as an intermediate step.
        - The global sampling rate `FS` is used.
    """
    wav_file = f"{name}.wav"
    mp3_file = f"{name}.mp3"

    signal = np.concatenate([silence(0.10), signal, silence(0.10)])

    write(wav_file, FS, (signal * 32767).astype(np.int16))

    audio = AudioSegment.from_wav(wav_file)
    audio = audio.set_channels(1)
    audio.export(mp3_file, format="mp3", bitrate=bitrate)


def main() -> None:
    """
    Generate and export predefined scanner notification sounds.

    This function creates two audio signals:
    - A short confirmation beep indicating a successful scan.
    - A repeating beep pattern indicating a scan error.

    The generated signals are exported as MP3 files.
    """

    scanner_ok = piezo_beep(2200, 0.10)

    # Diagnostic plots: start and end regions
    n_samples = int(0.002 * FS)
    _, axs = plt.subplots(1, 2, figsize=(10, 4))

    axs[0].plot(scanner_ok[:n_samples])
    axs[0].set_title("Start")

    axs[1].plot(scanner_ok[-n_samples:])
    axs[1].set_title("End")

    for ax in axs:
        ax.axhline(0, color="gray", linestyle="--")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Amplitude")

    plt.tight_layout()
    plt.show()

    export_mp3("valid_ticket", scanner_ok)

    scanner_error = np.concatenate(
        [
            piezo_beep(2200, 0.09),
            silence(0.06),
            piezo_beep(2200, 0.09),
            silence(0.06),
            piezo_beep(2200, 0.09),
        ]
    )

    export_mp3("invalid_ticket", scanner_error)


if __name__ == "__main__":
    main()

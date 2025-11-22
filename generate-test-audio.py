#!/usr/bin/env python3
"""
Generate a test audio file for the WebGPU audio waterfall demo.
Creates a WAV file with a chirp (frequency sweep) from 200 Hz to 2000 Hz.
"""

import struct
import math

def write_wav_file(filename, sample_rate, audio_data):
    """Write audio data to a WAV file."""
    num_samples = len(audio_data)
    num_channels = 1
    bits_per_sample = 16

    # Convert float audio data (-1.0 to 1.0) to 16-bit PCM
    pcm_data = []
    for sample in audio_data:
        # Clamp to [-1.0, 1.0]
        sample = max(-1.0, min(1.0, sample))
        # Convert to 16-bit integer
        pcm_value = int(sample * 32767)
        pcm_data.append(pcm_value)

    # WAV file header
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    with open(filename, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))  # File size - 8
        f.write(b'WAVE')

        # fmt subchunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # Subchunk size
        f.write(struct.pack('<H', 1))   # Audio format (1 = PCM)
        f.write(struct.pack('<H', num_channels))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', byte_rate))
        f.write(struct.pack('<H', block_align))
        f.write(struct.pack('<H', bits_per_sample))

        # data subchunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))

        # Write PCM data
        for pcm_value in pcm_data:
            f.write(struct.pack('<h', pcm_value))

def generate_chirp(sample_rate, duration, start_freq, end_freq):
    """Generate a frequency sweep (chirp) signal."""
    num_samples = int(sample_rate * duration)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        # Linear frequency sweep
        freq = start_freq + (end_freq - start_freq) * (t / duration)
        # Generate sine wave at current frequency
        sample = 0.5 * math.sin(2 * math.pi * freq * t)
        audio_data.append(sample)

    return audio_data

def main():
    sample_rate = 44100  # Hz
    duration = 3.0       # seconds
    start_freq = 200     # Hz
    end_freq = 2000      # Hz

    print(f"Generating test audio file...")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration} seconds")
    print(f"  Frequency sweep: {start_freq} Hz -> {end_freq} Hz")

    audio_data = generate_chirp(sample_rate, duration, start_freq, end_freq)

    filename = "test-audio.wav"
    write_wav_file(filename, sample_rate, audio_data)

    print(f"✓ Created {filename}")
    print(f"  File size: {len(audio_data) * 2} bytes")

if __name__ == "__main__":
    main()

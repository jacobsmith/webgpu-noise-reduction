#!/usr/bin/env python3
"""
Create test audio dataset for noise reduction testing.

Downloads speech samples and background noise, then mixes them at various SNR levels.
Supports LibriVox (free speech) and Freesound (background noise with API key).
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import struct
import math
import random

# Configuration
OUTPUT_DIR = "test-audio-dataset"
FREESOUND_API_KEY = ""  # Add your API key here or pass via command line

# SNR levels to test (in dB)
SNR_LEVELS = [0, 5, 10, 15, 20]

# Sample rate for all output files
SAMPLE_RATE = 44100


class AudioFile:
    """Simple WAV file handler."""

    def __init__(self, sample_rate, audio_data):
        self.sample_rate = sample_rate
        self.audio_data = audio_data  # Float32 array, -1.0 to 1.0

    @staticmethod
    def read_wav(filename):
        """Read a WAV file and return AudioFile object."""
        with open(filename, 'rb') as f:
            # Read RIFF header
            riff = f.read(4)
            if riff != b'RIFF':
                raise ValueError("Not a valid WAV file")

            file_size = struct.unpack('<I', f.read(4))[0]
            wave = f.read(4)
            if wave != b'WAVE':
                raise ValueError("Not a valid WAV file")

            # Read fmt subchunk
            fmt = f.read(4)
            if fmt != b'fmt ':
                raise ValueError("fmt subchunk not found")

            fmt_size = struct.unpack('<I', f.read(4))[0]
            audio_format = struct.unpack('<H', f.read(2))[0]
            num_channels = struct.unpack('<H', f.read(2))[0]
            sample_rate = struct.unpack('<I', f.read(4))[0]
            byte_rate = struct.unpack('<I', f.read(4))[0]
            block_align = struct.unpack('<H', f.read(2))[0]
            bits_per_sample = struct.unpack('<H', f.read(2))[0]

            # Skip any extra fmt bytes
            if fmt_size > 16:
                f.read(fmt_size - 16)

            # Find data subchunk
            while True:
                chunk_id = f.read(4)
                if not chunk_id:
                    raise ValueError("data subchunk not found")
                chunk_size = struct.unpack('<I', f.read(4))[0]

                if chunk_id == b'data':
                    break
                # Skip this chunk
                f.read(chunk_size)

            # Read audio data
            num_samples = chunk_size // (bits_per_sample // 8) // num_channels
            audio_data = []

            if bits_per_sample == 16:
                for _ in range(num_samples):
                    # Read all channels and average to mono
                    sample_sum = 0
                    for _ in range(num_channels):
                        pcm_value = struct.unpack('<h', f.read(2))[0]
                        sample_sum += pcm_value / 32768.0
                    audio_data.append(sample_sum / num_channels)
            else:
                raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")

        return AudioFile(sample_rate, audio_data)

    def write_wav(self, filename):
        """Write audio data to WAV file."""
        num_samples = len(self.audio_data)
        num_channels = 1
        bits_per_sample = 16

        # Convert float to 16-bit PCM
        pcm_data = []
        for sample in self.audio_data:
            sample = max(-1.0, min(1.0, sample))
            pcm_value = int(sample * 32767)
            pcm_data.append(pcm_value)

        byte_rate = self.sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = num_samples * block_align

        with open(filename, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + data_size))
            f.write(b'WAVE')

            # fmt subchunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))
            f.write(struct.pack('<H', 1))  # PCM
            f.write(struct.pack('<H', num_channels))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', byte_rate))
            f.write(struct.pack('<H', block_align))
            f.write(struct.pack('<H', bits_per_sample))

            # data subchunk
            f.write(b'data')
            f.write(struct.pack('<I', data_size))

            for pcm_value in pcm_data:
                f.write(struct.pack('<h', pcm_value))

    def resample(self, target_rate):
        """Resample audio to target sample rate (simple linear interpolation)."""
        if self.sample_rate == target_rate:
            return self

        ratio = target_rate / self.sample_rate
        new_length = int(len(self.audio_data) * ratio)
        resampled = []

        for i in range(new_length):
            src_index = i / ratio
            src_floor = int(src_index)
            src_ceil = min(src_floor + 1, len(self.audio_data) - 1)
            fraction = src_index - src_floor

            sample = (self.audio_data[src_floor] * (1 - fraction) +
                     self.audio_data[src_ceil] * fraction)
            resampled.append(sample)

        return AudioFile(target_rate, resampled)

    def trim_or_pad(self, target_length):
        """Trim or pad audio to target length."""
        if len(self.audio_data) == target_length:
            return self
        elif len(self.audio_data) > target_length:
            # Trim
            return AudioFile(self.sample_rate, self.audio_data[:target_length])
        else:
            # Pad with zeros
            padded = self.audio_data + [0.0] * (target_length - len(self.audio_data))
            return AudioFile(self.sample_rate, padded)

    def loop_to_length(self, target_length):
        """Loop audio to reach target length."""
        if len(self.audio_data) >= target_length:
            return AudioFile(self.sample_rate, self.audio_data[:target_length])

        looped = []
        while len(looped) < target_length:
            remaining = target_length - len(looped)
            looped.extend(self.audio_data[:remaining])

        return AudioFile(self.sample_rate, looped)


def generate_noise(duration, noise_type='white'):
    """Generate synthetic noise."""
    num_samples = int(SAMPLE_RATE * duration)

    if noise_type == 'white':
        # White noise - equal power at all frequencies
        noise = [random.uniform(-1.0, 1.0) for _ in range(num_samples)]

    elif noise_type == 'pink':
        # Pink noise - 1/f noise (approximate using simple filter)
        noise = []
        b0, b1, b2 = 0.0, 0.0, 0.0
        for _ in range(num_samples):
            white = random.uniform(-1.0, 1.0)
            b0 = 0.99765 * b0 + white * 0.0990460
            b1 = 0.96300 * b1 + white * 0.2965164
            b2 = 0.57000 * b2 + white * 1.0526913
            pink = b0 + b1 + b2 + white * 0.1848
            noise.append(pink / 5.0)  # Normalize

    elif noise_type == 'brown':
        # Brown noise - 1/f^2 noise
        noise = []
        last = 0.0
        for _ in range(num_samples):
            white = random.uniform(-0.02, 0.02)
            last = last + white
            last = max(-1.0, min(1.0, last))  # Clamp
            noise.append(last)

    else:
        raise ValueError(f"Unknown noise type: {noise_type}")

    return AudioFile(SAMPLE_RATE, noise)


def download_file(url, output_path, description="file"):
    """Download a file with progress indication."""
    print(f"  Downloading {description}...")
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"  ✓ Downloaded to {output_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error downloading: {e}")
        return False


def download_librivox_sample(output_dir):
    """
    Download a speech sample from LibriVox.
    Uses a known public domain audiobook URL.
    """
    print("\n[1/3] Downloading speech sample from LibriVox...")

    # Using a short sample from LibriVox's archive
    # This is a public domain recording
    url = "https://ia600300.us.archive.org/11/items/rumpelstiltskin_1711_librivox/rumpelstiltskin_01_grimm_64kb.mp3"

    mp3_path = os.path.join(output_dir, "speech_sample.mp3")
    wav_path = os.path.join(output_dir, "speech_clean.wav")

    if os.path.exists(wav_path):
        print(f"  Speech sample already exists: {wav_path}")
        return wav_path

    # Download MP3
    if not download_file(url, mp3_path, "LibriVox speech sample (MP3)"):
        return None

    # Convert MP3 to WAV using ffmpeg (if available)
    print("  Converting MP3 to WAV...")
    print("  NOTE: This requires ffmpeg. If you don't have it:")
    print("        - macOS: brew install ffmpeg")
    print("        - Linux: sudo apt-get install ffmpeg")
    print("        - Or manually convert the MP3 to WAV and place at:", wav_path)

    import subprocess
    try:
        subprocess.run([
            'ffmpeg', '-i', mp3_path, '-ar', str(SAMPLE_RATE),
            '-ac', '1', '-t', '10', wav_path, '-y'
        ], check=True, capture_output=True)
        print(f"  ✓ Converted to {wav_path}")
        os.remove(mp3_path)
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  ✗ ffmpeg not available or conversion failed")
        print(f"    Please manually convert {mp3_path} to WAV format")
        return None


def download_freesound_noise(api_key, output_dir):
    """Download background noise from Freesound.org."""
    print("\n[2/3] Downloading background noise from Freesound...")

    if not api_key:
        print("  ⚠ No Freesound API key provided. Skipping Freesound download.")
        print("    Get a free API key at: https://freesound.org/apiv2/apply/")
        return None

    # Search for cafe/restaurant ambience
    search_query = "cafe ambience"
    url = f"https://freesound.org/apiv2/search/text/?query={urllib.parse.quote(search_query)}&filter=duration:[5.0 TO 30.0]&fields=id,name,previews&token={api_key}"

    try:
        print(f"  Searching Freesound for: {search_query}")
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        if not data.get('results'):
            print("  ✗ No results found")
            return None

        # Get first result
        sound = data['results'][0]
        sound_id = sound['id']
        sound_name = sound['name']
        preview_url = sound['previews']['preview-hq-mp3']

        print(f"  Found: {sound_name} (ID: {sound_id})")

        mp3_path = os.path.join(output_dir, f"noise_{sound_id}.mp3")
        wav_path = os.path.join(output_dir, "noise_cafe.wav")

        if os.path.exists(wav_path):
            print(f"  Noise already exists: {wav_path}")
            return wav_path

        # Download preview
        if not download_file(preview_url, mp3_path, "Freesound noise (MP3)"):
            return None

        # Convert to WAV
        print("  Converting MP3 to WAV...")
        import subprocess
        try:
            subprocess.run([
                'ffmpeg', '-i', mp3_path, '-ar', str(SAMPLE_RATE),
                '-ac', '1', wav_path, '-y'
            ], check=True, capture_output=True)
            print(f"  ✓ Converted to {wav_path}")
            os.remove(mp3_path)
            return wav_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ✗ ffmpeg conversion failed")
            return None

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def generate_synthetic_noise(output_dir):
    """Generate synthetic background noise as fallback."""
    print("\n[2/3] Generating synthetic background noise...")

    noise_types = {
        'white': "White noise (equal power at all frequencies)",
        'pink': "Pink noise (1/f, natural background)",
        'brown': "Brown noise (1/f², deep rumble)"
    }

    generated_files = []

    for noise_type, description in noise_types.items():
        output_path = os.path.join(output_dir, f"noise_{noise_type}.wav")

        if os.path.exists(output_path):
            print(f"  {description} already exists")
            generated_files.append(output_path)
            continue

        print(f"  Generating {description}...")
        noise = generate_noise(10.0, noise_type)
        noise.write_wav(output_path)
        print(f"  ✓ Saved to {output_path}")
        generated_files.append(output_path)

    return generated_files


def mix_audio_with_snr(speech, noise, snr_db):
    """Mix speech with noise at specified SNR level."""
    # Calculate RMS (root mean square) of speech
    speech_rms = math.sqrt(sum(s*s for s in speech.audio_data) / len(speech.audio_data))

    # Calculate RMS of noise
    noise_rms = math.sqrt(sum(n*n for n in noise.audio_data) / len(noise.audio_data))

    # Calculate noise scaling factor for desired SNR
    # SNR = 20 * log10(speech_rms / noise_rms)
    # noise_scale = speech_rms / (noise_rms * 10^(SNR/20))
    snr_linear = 10 ** (snr_db / 20)
    noise_scale = speech_rms / (noise_rms * snr_linear) if noise_rms > 0 else 0

    # Mix
    mixed = []
    for i in range(len(speech.audio_data)):
        mixed_sample = speech.audio_data[i] + noise.audio_data[i] * noise_scale
        # Clip to prevent distortion
        mixed_sample = max(-1.0, min(1.0, mixed_sample))
        mixed.append(mixed_sample)

    return AudioFile(speech.sample_rate, mixed)


def create_mixed_samples(speech_path, noise_paths, output_dir):
    """Create mixed speech+noise samples at various SNR levels."""
    print("\n[3/3] Creating mixed samples at various SNR levels...")

    if not speech_path or not os.path.exists(speech_path):
        print("  ✗ Speech file not available")
        return

    if not noise_paths:
        print("  ✗ No noise files available")
        return

    # Load speech
    print(f"  Loading speech: {speech_path}")
    speech = AudioFile.read_wav(speech_path)
    speech = speech.resample(SAMPLE_RATE)

    # Limit speech to 10 seconds for testing
    max_length = SAMPLE_RATE * 10
    if len(speech.audio_data) > max_length:
        speech = speech.trim_or_pad(max_length)

    print(f"  Speech duration: {len(speech.audio_data) / SAMPLE_RATE:.2f}s")

    # Process each noise type
    for noise_path in noise_paths:
        if not os.path.exists(noise_path):
            continue

        noise_name = os.path.splitext(os.path.basename(noise_path))[0]
        print(f"\n  Processing noise: {noise_name}")

        # Load and prepare noise
        noise = AudioFile.read_wav(noise_path)
        noise = noise.resample(SAMPLE_RATE)
        noise = noise.loop_to_length(len(speech.audio_data))

        # Create mixes at different SNR levels
        for snr_db in SNR_LEVELS:
            output_filename = f"mixed_{noise_name}_snr{snr_db}db.wav"
            output_path = os.path.join(output_dir, output_filename)

            if os.path.exists(output_path):
                print(f"    SNR {snr_db}dB: already exists")
                continue

            mixed = mix_audio_with_snr(speech, noise, snr_db)
            mixed.write_wav(output_path)
            print(f"    SNR {snr_db}dB: ✓ {output_filename}")

    # Copy clean speech to output directory
    clean_output = os.path.join(output_dir, "speech_clean.wav")
    if not os.path.exists(clean_output):
        speech.write_wav(clean_output)
        print(f"\n  ✓ Saved clean speech: speech_clean.wav")


def main():
    global FREESOUND_API_KEY

    print("=" * 60)
    print("Test Audio Dataset Generator")
    print("for Speech Noise Reduction Testing")
    print("=" * 60)

    # Check for API key in command line
    if len(sys.argv) > 1:
        FREESOUND_API_KEY = sys.argv[1]
        print(f"\nUsing Freesound API key from command line")
    elif FREESOUND_API_KEY:
        print(f"\nUsing Freesound API key from script")
    else:
        print(f"\nNo Freesound API key provided (optional)")
        print("Get one at: https://freesound.org/apiv2/apply/")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}/")

    # Step 1: Download speech
    speech_path = download_librivox_sample(OUTPUT_DIR)

    # Step 2: Download or generate noise
    noise_paths = []

    if FREESOUND_API_KEY:
        freesound_noise = download_freesound_noise(FREESOUND_API_KEY, OUTPUT_DIR)
        if freesound_noise:
            noise_paths.append(freesound_noise)

    # Always generate synthetic noise as fallback/supplement
    synthetic_noise = generate_synthetic_noise(OUTPUT_DIR)
    noise_paths.extend(synthetic_noise)

    # Step 3: Create mixed samples
    create_mixed_samples(speech_path, noise_paths, OUTPUT_DIR)

    # Summary
    print("\n" + "=" * 60)
    print("Dataset Generation Complete!")
    print("=" * 60)
    print(f"\nGenerated files in: {OUTPUT_DIR}/")
    print("\nFiles created:")
    print("  - speech_clean.wav (original clean speech)")
    for noise_path in noise_paths:
        noise_name = os.path.splitext(os.path.basename(noise_path))[0]
        print(f"  - {noise_name}.wav (noise source)")
        for snr_db in SNR_LEVELS:
            print(f"    - mixed_{noise_name}_snr{snr_db}db.wav")

    print("\nTo use in the waterfall visualizer:")
    print(f"  1. Copy files from {OUTPUT_DIR}/ to web-gpu/")
    print("  2. Update TEST_FILE_PATH in webgpu-audio-waterfall.html")
    print("  3. python3 dev-server.py")
    print("  4. Open http://localhost:8000/webgpu-audio-waterfall.html")


if __name__ == "__main__":
    main()

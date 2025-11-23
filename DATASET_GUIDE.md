# Test Audio Dataset Guide

Guide for creating speech + noise test datasets for noise reduction development.

## Quick Start

### Option 1: Without Freesound (Synthetic noise only)

```bash
python3 create-test-audio-dataset.py
```

This will:
- Download a speech sample from LibriVox (public domain)
- Generate synthetic noise (white, pink, brown)
- Mix speech + noise at SNR levels: 0dB, 5dB, 10dB, 15dB, 20dB
- Save everything to `test-audio-dataset/`

### Option 2: With Freesound (Real background noise)

1. Get a free API key: https://freesound.org/apiv2/apply/

2. **Recommended:** Add to `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key:
   # FREESOUND_API_KEY=your_actual_api_key_here
   ```

3. Run the script:
   ```bash
   python3 create-test-audio-dataset.py
   ```

**Alternative:** Pass API key via command line:
```bash
python3 create-test-audio-dataset.py YOUR_API_KEY
```

This downloads real cafe/restaurant ambience from Freesound plus generates synthetic noise.

## Requirements

**Required:**
- Python 3.x

**Optional (for downloading samples):**
- `ffmpeg` - For converting MP3 to WAV
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`
  - Windows: Download from https://ffmpeg.org/

**Without ffmpeg:**
The script will still generate synthetic noise and can work with WAV files you provide manually.

## Output Files

After running, you'll have in `test-audio-dataset/`:

```
speech_clean.wav                    # Original clean speech
noise_white.wav                     # White noise
noise_pink.wav                      # Pink noise (natural background)
noise_brown.wav                     # Brown noise (deep rumble)
noise_cafe.wav                      # Real cafe noise (if Freesound used)

# Mixed samples at different SNR levels:
mixed_noise_white_snr0db.wav        # Very noisy (0dB SNR)
mixed_noise_white_snr5db.wav
mixed_noise_white_snr10db.wav
mixed_noise_white_snr15db.wav
mixed_noise_white_snr20db.wav       # Less noisy (20dB SNR)

# ... same for pink, brown, cafe
```

## Understanding SNR Levels

**SNR (Signal-to-Noise Ratio)** in dB:
- **0 dB**: Speech and noise have equal power (very challenging)
- **5 dB**: Speech slightly louder than noise (challenging)
- **10 dB**: Speech moderately louder (typical noisy environment)
- **15 dB**: Speech clearly louder (mild noise)
- **20 dB**: Speech much louder than noise (easy case)

## Using with the Waterfall Visualizer

1. **Copy test files:**
   ```bash
   cp test-audio-dataset/mixed_noise_pink_snr10db.wav .
   ```

2. **Update test file path** in `webgpu-audio-waterfall.html` (line ~813):
   ```javascript
   const TEST_FILE_PATH = './mixed_noise_pink_snr10db.wav';
   ```

3. **Run dev server:**
   ```bash
   python3 dev-server.py
   ```

4. **Test your noise reduction:**
   - Open http://localhost:8000/webgpu-audio-waterfall.html
   - Click "Load Test File"
   - Implement your noise reduction in `processAudioBuffer()`
   - Click "Process Audio"
   - Compare input vs output with waterfalls and playback

## Noise Types Explained

**White Noise:**
- Equal power at all frequencies
- Sounds like "static" or "hiss"
- Good for testing general noise reduction

**Pink Noise:**
- Power decreases with frequency (1/f)
- More natural than white noise
- Similar to rain, wind, or distant traffic
- **Recommended for initial testing**

**Brown Noise:**
- Power decreases faster with frequency (1/f²)
- Deep, rumbling sound
- Like ocean waves or heavy wind

**Cafe/Restaurant (from Freesound):**
- Real-world recording
- Multiple speakers, dishes, ambience
- **Best for realistic testing**

## Tips for Noise Reduction Development

1. **Start with high SNR (15-20dB)**
   - Easier to see what your algorithm does
   - Build confidence before tackling harder cases

2. **Test on multiple noise types**
   - Pink noise: General broadband noise
   - Cafe: Speech-like interference
   - White noise: Worst case scenario

3. **Compare before/after**
   - Use the dual waterfall view
   - Check if you're removing noise without damaging speech
   - Listen to both - visual isn't everything!

4. **Watch for artifacts**
   - Musical noise (random tones)
   - Speech distortion
   - Muffled quality

## Advanced: Custom Noise Sources

You can add your own noise files:

1. Place WAV files (44.1kHz, mono recommended) in `test-audio-dataset/`
2. Name them `noise_customname.wav`
3. The script will automatically mix them with speech on next run

Or modify the script to download from other sources!

## Troubleshooting

**"ffmpeg not found":**
- Install ffmpeg or manually convert MP3s to WAV
- Or use synthetic noise only (works without ffmpeg)

**"No results found" from Freesound:**
- Check your API key
- Try different search terms in the script
- Or use synthetic noise

**"Speech file not available":**
- Check internet connection
- Manually download speech and save as `test-audio-dataset/speech_clean.wav`

## Example Workflow

```bash
# 1. Generate dataset (first time)
python3 create-test-audio-dataset.py

# 2. Copy a test file
cp test-audio-dataset/mixed_noise_pink_snr10db.wav ./test-audio.wav

# 3. Start dev server
python3 dev-server.py

# 4. Open browser, test your algorithm
# http://localhost:8000/webgpu-audio-waterfall.html

# 5. Try harder cases
cp test-audio-dataset/mixed_noise_pink_snr5db.wav ./test-audio.wav
# Refresh and test again
```

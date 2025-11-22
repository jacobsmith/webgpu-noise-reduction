# WebGPU Audio Waterfall

Dual waterfall visualization for comparing input and processed audio using WebGPU compute shaders.

## Quick Start

```bash
# 1. Generate test audio file
python3 generate-test-audio.py

# 2. Start dev server (required for "Load Test File" button)
python3 dev-server.py

# 3. Open in browser
# http://localhost:8000/webgpu-audio-waterfall.html

# 4. Click "Load Test File" → "Process Audio" → "Play Input"/"Play Output"
```

## Features

- **Dual Waterfall Display**: Side-by-side visualization of input and output audio
- **Multiple Input Methods**:
  - Record from microphone
  - Upload audio files (WAV, MP3, etc.)
  - Quick-load test file for development
- **Audio Processing**: Placeholder function for custom audio processing algorithms
- **Playback**: Listen to input and output audio to compare differences

## Usage

**Important:** For the "Load Test File" button to work, you must run the dev server:
```bash
python3 dev-server.py
```
Then open http://localhost:8000/webgpu-audio-waterfall.html

### Option 1: Record from Microphone
1. Click "Start Recording"
2. Speak or play audio into your microphone
3. Click "Stop" when done
4. Click "Process Audio" to run processing
5. Use "Play Input" and "Play Output" to compare

### Option 2: Upload Audio File
1. Click "Choose File" and select an audio file
2. Wait for the file to load and visualize
3. Click "Process Audio" to run processing
4. Use "Play Input" and "Play Output" to compare

### Option 3: Load Test File (for development)
1. Generate test audio: `python3 generate-test-audio.py`
2. Start dev server: `python3 dev-server.py`
3. Open http://localhost:8000/webgpu-audio-waterfall.html
4. Click "Load Test File" button
5. Click "Process Audio" to run processing
6. Use "Play Input" and "Play Output" to compare

## Customization

### Change Test File Path
Edit the `TEST_FILE_PATH` constant in `webgpu-audio-waterfall.html` (line ~813):
```javascript
const TEST_FILE_PATH = './your-custom-test-file.wav';
```

### Add Your Audio Processing
Replace the `processAudioBuffer()` function in `webgpu-audio-waterfall.html` (line ~986):
```javascript
function processAudioBuffer(inputData) {
    // Your processing here
    // - Noise reduction
    // - Equalization
    // - Compression
    // - etc.

    return processedData; // Float32Array
}
```

## Files

- `webgpu-audio-waterfall.html` - Main application
- `dev-server.py` - Development HTTP server with CORS support (required for "Load Test File")
- `generate-test-audio.py` - Script to generate simple test audio (3s chirp from 200-2000 Hz)
- `create-test-audio-dataset.py` - Advanced: Generate speech + noise datasets for noise reduction testing
- `test-audio.wav` - Generated test audio file (created by running the Python script)
- `DATASET_GUIDE.md` - Complete guide for creating noise reduction test datasets

## Requirements

- WebGPU-compatible browser (Chrome 113+, Edge 113+)
- Python 3.x (for dev server and test audio generation)
- For microphone recording: HTTPS or localhost
- For "Load Test File" button: Dev server must be running (`python3 dev-server.py`)
- For file upload: No special requirements (works without dev server)

## Noise Reduction Testing

For developing speech noise reduction algorithms:

### Generate Test Dataset

```bash
# Without Freesound API key (uses synthetic noise)
python3 create-test-audio-dataset.py

# With Freesound API key (includes real background noise)
python3 create-test-audio-dataset.py YOUR_API_KEY
```

This creates:
- Clean speech sample (from LibriVox)
- Noise sources (white, pink, brown, cafe ambience)
- Mixed samples at SNR levels: 0dB, 5dB, 10dB, 15dB, 20dB

See [DATASET_GUIDE.md](DATASET_GUIDE.md) for complete documentation.

### Recommended Workflow

1. Generate dataset: `python3 create-test-audio-dataset.py`
2. Copy test file: `cp test-audio-dataset/mixed_noise_pink_snr10db.wav ./test-audio.wav`
3. Update `processAudioBuffer()` with your noise reduction algorithm
4. Test visually with waterfalls and aurally with playback buttons
5. Try different SNR levels and noise types

## Technical Details

- FFT Size: 1024 samples
- Sample Rate: 44,100 Hz
- Frequency Range: 0-4,000 Hz (optimized for speech)
- Waterfall Resolution: ~186 frequency bins × 512 time rows

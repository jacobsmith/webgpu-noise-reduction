# WebGPU Audio Noise Reduction

Real-time speech noise reduction using WebGPU compute shaders with spectral subtraction and dual waterfall visualization.

**[Live Demo on GitHub Pages](https://[your-username].github.io/webgpu-noise-reduction/webgpu-audio-waterfall.html)** _(requires Chrome 113+ or Edge 113+)_

## Preamble

This repo is my capstone project for [GPU Programming Specialization by John Hopkins University](https://www.coursera.org/specializations/gpu-programming).

I personally am a licensed amateur radio operator and volunteer with my local County Emergency Management group. As part of my experience in radio, we are often dealing with difficult to interpret signals - we may be talking to people hundreds or thousands of miles away and there can be a great deal of signal degradation. I wanted to utilize what I've learned in this GPU course to learn more about audio processing, specifically around noise reduction.

The overall architecture is as follows:

1. User selects an audio file (either from the pre-made test set or an uploaded file)
2. The file is sliced up into "chunks" based on FFT_SIZE
   2a. The default FFT_SIZE is 1024, meaning we read 1,024 samples of the audio. At a 44,100 hz sample rate, that is equal to ~23 milliseconds of audio
3. Each of those chunks is then passed through an Fast Fourier Transform (FFT), which transforms the audio from a time-domain into a frequency domain (that gives us the amount of sound produced in that given "bin" of frequencies)
4. We then pass it through a noise pass, which updates the `noiseProfile` with the amount of noise heard for each frequency domain.
   4a. This updates over time through the use of a tuneable `ALPHA_DECAY` parameter.
5. The Noise Reduction step takes each FFT bin and subtracts the noise parameter we have currently learned multipled by a `NOISE_SUPRESSION_FACTOR` - this is another parameter that can adjust how "aggressive" the noise reduction is.
   5a. We also have a `NOISE_FLOOR` parameter that can be adjusted to ensure we don't drop the audio below a certain threshold. This can help reduce a "warbling" effect if frequencies come in and out of the cutoff value.
6. Finally, we perform an inverse FFT to turn our frequency-domain data back into time-domain data.
7. This time-domain data is then reconstructed into an audio file and playable via the UI.

## Use of AI

In an effort to be totally transparent, this project did utilize AI in the ideation and some parts of the execution phases. The UI was entirely created by AI (at my direction) along with some of the "boilerplate" of working with WebGPU and FFT/InverseFFT processes. All of the noise reduction portions were translated from pseudocode into executable WGSL by myself, and then helped debug with the use of AI. A write up of the bugs encountered and some lessons learned is available at the BUGS_FIXED.md file in this repo.

## Next steps

Overall, I'd love to run additional benchmarking to see how this performs on different devices. I would also like to customize it to focus on types of noise particularly present in Amateur Radio. This has been a great learning experience and a wonderful introduction to both WebGPU and audio processing.

## Overview

This project implements GPU-accelerated audio noise reduction for speech enhancement. It uses:

- **Spectral Subtraction** for noise removal
- **Minimum Statistics** for adaptive noise estimation
- **WebGPU Compute Shaders** for real-time processing
- **Dual Waterfall Visualization** to compare input vs output

Perfect for learning GPU audio processing, testing noise reduction algorithms, or experimenting with different noise types and SNR levels.

## Quick Start

### Online (GitHub Pages)

1. Visit the live demo (Chrome 113+ or Edge 113+)
2. Select noise type and SNR level
3. Click "Load Test File" → "Process Audio"
4. Adjust parameters and re-process to hear differences

### Local Development

```bash
# 1. Generate test audio files
python3 create-test-audio-dataset.py

# 2. Start dev server
python3 dev-server.py

# 3. Open in browser
# http://localhost:8000/webgpu-audio-waterfall.html
```

## Features

### Noise Reduction Algorithm

- **Spectral Subtraction**: Removes noise in frequency domain
- **Minimum Statistics**: Learns noise profile adaptively over time
- **Configurable Parameters**:
  - **Noise Suppression Factor** (0-5): How aggressively to subtract noise
  - **Noise Floor** (0-0.5): Minimum gain to reduce musical noise artifacts
  - **Alpha Decay** (0.001-0.1): Noise profile learning rate

### Audio Sources

- **Microphone Recording**: Record live audio for testing
- **File Upload**: Drag & drop any audio file (WAV, MP3, etc.)
- **Test Dataset**: 20 pre-generated test files:
  - 4 noise types: Pink, White, Brown, Cafe Ambience
  - 5 SNR levels each: 0dB, 5dB, 10dB, 15dB, 20dB

### Visualization

- **Dual Waterfall Display**: Side-by-side input/output comparison
- **Frequency Range**: 0-4,000 Hz (optimized for speech)
- **Real-time Updates**: See processing results immediately

### Playback & Comparison

- Play input and output audio
- Visual waterfall comparison
- RMS ratio calculation
- Sample-level difference logging

## Algorithm Details

The noise reduction pipeline uses four GPU compute shaders:

1. **FFT** (Time → Frequency): Convert audio chunks to frequency domain
2. **Noise Profile Update**: Learn minimum magnitude per frequency bin
3. **Noise Reduction**: Apply spectral subtraction
   ```wgsl
   cleanMagnitude = max(0, signalMagnitude - suppressionFactor * noiseMagnitude)
   gain = max(noiseFloor, cleanMagnitude / signalMagnitude)
   output = input * gain
   ```
4. **IFFT** (Frequency → Time): Convert back to time domain

See [BUGS_FIXED.md](BUGS_FIXED.md) for detailed documentation of implementation challenges and solutions.

## Usage

### Processing Audio

1. **Load Audio**:

   - Click "Load Test File" and select noise type/SNR
   - OR upload your own file
   - OR record from microphone

2. **Adjust Parameters**:

   - **Noise Suppression**: Higher = more aggressive (but more artifacts)
   - **Noise Floor**: Higher = smoother (but more residual noise)
   - **Alpha Decay**: Lower = slower adaptation (more stable)
   - Click "Apply Parameters" to recreate GPU pipelines

3. **Process**:

   - Click "Process Audio"
   - Check console for diagnostics (parameters, RMS ratio)
   - Compare waterfalls visually

4. **Listen**:
   - Click "Play Input" to hear original noisy audio
   - Click "Play Output" to hear cleaned audio
   - Re-process with different parameters to experiment

### Parameter Tuning Tips

**For maximum noise removal:**

- Noise Suppression: 4-5
- Noise Floor: 0.05-0.1
- Alpha Decay: 0.001-0.01
- Trade-off: More artifacts (warbling/musical noise)

**For natural sound quality:**

- Noise Suppression: 2-3
- Noise Floor: 0.2-0.3
- Alpha Decay: 0.01-0.05
- Trade-off: Some residual noise remains

**For varying noise conditions:**

- Increase Alpha Decay (0.05-0.1) for faster adaptation
- Decrease for steady background noise (0.001-0.01)

## Test Dataset

The included test dataset contains 25 audio files for comprehensive testing:

**Noise Types:**

- **Pink Noise**: Natural 1/f spectrum (like rain or wind)
- **White Noise**: Equal power at all frequencies (hiss)
- **Brown Noise**: Low-frequency rumble (like ocean waves)
- **Cafe Ambience**: Real-world recording with speech-like interference

**SNR Levels:**

- 0 dB: Very challenging (noise as loud as speech)
- 5 dB: Challenging (noisy environment)
- 10 dB: Moderate (typical use case)
- 15 dB: Mild noise
- 20 dB: Easy case (clean speech)

Generate custom datasets with:

```bash
python3 create-test-audio-dataset.py
```

See [DATASET_GUIDE.md](DATASET_GUIDE.md) for details.

## Files

- `webgpu-audio-waterfall.html` - Main application with GPU shaders
- `BUGS_FIXED.md` - Detailed bug documentation and lessons learned
- `DATASET_GUIDE.md` - Test dataset creation guide
- `create-test-audio-dataset.py` - Generate speech + noise test files
- `generate-test-audio.py` - Simple chirp generator
- `dev-server.py` - Local development server
- `test-audio-dataset/` - 25 pre-generated test files (~21 MB)

## Requirements

**Browser:**

- Chrome 113+ or Edge 113+ (WebGPU support required)
- HTTPS or localhost (for microphone access)

**Local Development:**

- Python 3.x (for dev server and dataset generation)
- Optional: ffmpeg (for MP3→WAV conversion in dataset script)

## Technical Details

- **FFT Size**: 1024 samples
- **Sample Rate**: 44,100 Hz
- **Frequency Range**: 0-4,000 Hz (speech optimized)
- **Waterfall Resolution**: 92 frequency bins × 512 time rows
- **Processing**: Fully GPU-accelerated (data stays on GPU)
- **Latency**: Frame-by-frame processing (~23ms chunks)

## GitHub Pages Deployment

Already configured! Just enable in your repo settings:

1. Settings → Pages
2. Source: Deploy from branch
3. Branch: main → Save
4. Access at: `https://[username].github.io/web-gpu/webgpu-audio-waterfall.html`

The test dataset is included in the repo, so the "Load Test File" button works immediately.

## Learning Resources

This project documents several GPU programming challenges:

- **Buffer initialization**: Must initialize with meaningful values (not zeros)
- **Array bounds**: Match loop bounds to actual buffer sizes
- **Dispatch sizes**: Must match shader workgroup configuration
- **Buffer usage flags**: Need `COPY_SRC` for debugging GPU data
- **Algorithm design**: Binary gate ≠ noise reduction; use spectral subtraction

See [BUGS_FIXED.md](BUGS_FIXED.md) for detailed explanations of each bug, root causes, and fixes.

## Future Enhancements

Potential improvements for learning:

- Voice Activity Detection (VAD) to only learn noise during silence
- Wiener filtering for better SNR-based gain
- Multi-taper spectral estimation for smoother results
- Gain smoothing over time to reduce artifacts
- Different window functions (Hann, Hamming, Blackman)

## License

MIT License - feel free to use for learning and experimentation.

## Acknowledgments

- LibriVox for public domain speech samples
- Freesound.org for real-world noise samples
- WebGPU community for excellent documentation

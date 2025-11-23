# WebGPU Noise Reduction - Critical Bugs Fixed

## Overview
During implementation of GPU-based audio noise reduction, three critical bugs prevented the algorithm from working. This document details each bug for future reference.

---

## Bug #1: Uninitialized Noise Profile Buffer

### Symptom
No perceivable difference between input and output audio after noise reduction processing.

### Root Cause
The `noiseProfile` buffer was created but never initialized, starting with undefined/zero values:

```javascript
noiseProfile = device.createBuffer({
    size: WATERFALL_WIDTH * 4,
    usage: GPUBufferUsage.STORAGE,
});
// Buffer contents: [0, 0, 0, 0, ...]
```

### Why This Broke the Algorithm
Minimum statistics works by tracking the minimum magnitude over time:

```wgsl
if (currentMagnitude < noiseProfile[k]) {
    noiseProfile[k] = currentMagnitude;  // New minimum
} else {
    noiseProfile[k] = noiseProfile[k] * (1.0 - alpha) + currentMagnitude * alpha;
}
```

**With zero initialization:**
- First frame: `noiseProfile[k] = 0`
- `currentMagnitude` (e.g., 0.5) is NOT less than 0
- Goes to else branch: `noiseProfile[k] = 0 * 0.99 + 0.5 * 0.01 = 0.005`
- This is artificially low!

**In noise reduction:**
```wgsl
let noiseMagnitude = noiseProfile[k];  // 0.005 (way too low!)
let signalMagnitude = length(fftBuffer[k]);  // 0.3 (actual signal)

if (signalMagnitude > noiseMagnitude) {  // ALWAYS TRUE!
    gain = SIGNAL_GAIN;  // Always 1.0 - no reduction!
}
```

### Fix
Initialize with high values so minimum statistics can decrease to actual noise floor:

```javascript
noiseProfile = device.createBuffer({
    size: WATERFALL_WIDTH * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
});

const initNoiseProfile = new Float32Array(WATERFALL_WIDTH);
initNoiseProfile.fill(1000.0);  // Start high
device.queue.writeBuffer(noiseProfile, 0, initNoiseProfile);
```

### Lesson Learned
**Always initialize GPU buffers with meaningful values.** Uninitialized buffers contain undefined data (often zeros), which can silently break algorithms that expect specific initial conditions.

---

## Bug #2: Out-of-Bounds Array Access

### Symptom
WebGPU validation errors or undefined behavior. Noise reduction still not working correctly.

### Root Cause
Shader was accessing `noiseProfile[k]` where `k` could be up to `FFT_SIZE` (1024), but `noiseProfile` only had `WATERFALL_WIDTH` (~93) elements:

```wgsl
// WRONG - processes all FFT bins
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let k = global_id.x;
    if (k >= FFT_SIZE) {  // k can be 0-1023
        return;
    }

    let currentMagnitude = length(fftBuffer[k]);

    // BUG: noiseProfile only has 93 elements!
    if (currentMagnitude < noiseProfile[k]) {  // Out of bounds when k >= 93
        noiseProfile[k] = currentMagnitude;
    }
}
```

### Why This Happened
Conceptual mismatch between buffer sizes:
- **FFT Buffer**: 1024 bins (0-22050 Hz at 44.1kHz sample rate)
- **Noise Profile**: 93 bins (0-4000 Hz speech range only)
- **Mistake**: Used `FFT_SIZE` instead of `WATERFALL_WIDTH` for loop bounds

### Fix

**Update Noise Profile Shader:**
```wgsl
const WATERFALL_WIDTH: u32 = 93;  // Only speech frequencies

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let k = global_id.x;
    if (k >= WATERFALL_WIDTH) {  // Now k is 0-92
        return;
    }

    let currentMagnitude = length(fftBuffer[k]);

    if (currentMagnitude < noiseProfile[k]) {  // Safe access
        noiseProfile[k] = currentMagnitude;
    }
}
```

**Update Noise Reduction Shader:**
```wgsl
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let k = global_id.x;
    if (k >= FFT_SIZE) {
        return;
    }

    var gain = SIGNAL_GAIN;

    // Only apply noise reduction to bins we have noise profile for
    if (k < WATERFALL_WIDTH) {
        let noiseMagnitude = noiseProfile[k];  // Safe access
        let signalMagnitude = length(fftBuffer[k]);

        if (signalMagnitude > noiseMagnitude) {
            gain = SIGNAL_GAIN;
        } else {
            gain = NOISE_GAIN;
        }
    }

    processedFFTBuffer[k] = fftBuffer[k] * gain;
}
```

### Lesson Learned
**Match array bounds to actual buffer sizes.** When working with different frequency ranges, be explicit about which buffer size controls loop bounds. Add bounds checking for safety.

---

## Bug #3: Incorrect Dispatch Workgroup Size

### Symptom
Related to Bug #2 - shader executed on more elements than buffer could hold.

### Root Cause
JavaScript dispatch code used wrong size constant:

```javascript
// WRONG - dispatches for 1024 elements
noiseUpdatePass.dispatchWorkgroups(Math.ceil(FFT_SIZE / 64));
// This runs shader on indices 0-1023, but buffer only has 93 elements!
```

### Why This Happened
Copy-paste error from FFT pipeline, which correctly uses `FFT_SIZE`. Forgot to adjust for smaller `noiseProfile` buffer.

### Fix
```javascript
// CORRECT - dispatches for 93 elements
noiseUpdatePass.dispatchWorkgroups(Math.ceil(WATERFALL_WIDTH / 64));
// This runs shader on indices 0-92, matching buffer size
```

### Lesson Learned
**Dispatch size must match shader bounds and buffer size.** The formula is:
```
dispatchWorkgroups(ceil(elementCount / workgroupSize))
```
Where `elementCount` is the actual number of elements to process, not necessarily the size of other buffers.

---

## Summary Table

| Bug | Impact | Root Cause | Fix |
|-----|--------|------------|-----|
| Uninitialized Buffer | No noise reduction | Started at 0 instead of high value | Initialize with 1000.0 |
| Out-of-Bounds Access | Undefined behavior | Used FFT_SIZE instead of WATERFALL_WIDTH | Check k < WATERFALL_WIDTH |
| Wrong Dispatch Size | Excessive shader invocations | Copy-paste from different pipeline | Use WATERFALL_WIDTH / 64 |

---

## Debugging Techniques Used

1. **Console Logging**: Added debug output to compare input/output samples
   ```javascript
   console.log('Input sample:', inputSample);
   console.log('Output sample:', outputSample);
   console.log('Difference:', outputSample.map((v, i) => Math.abs(v - inputSample[i])));
   ```

2. **Visual Comparison**: Checked if waterfall visualizations looked different

3. **Extreme Parameter Testing**: Set `NOISE_GAIN = 0.0` to make effect obvious

4. **Code Review**: Traced data flow from buffer creation → shader → dispatch

5. **Buffer Size Analysis**: Listed all buffer sizes to find mismatches:
   - `audioBuffer`: 1024 floats
   - `fftBuffer`: 1024 complex (2048 floats)
   - `noiseProfile`: 93 floats ← smaller!

---

## Testing After Fixes

**Expected Behavior:**
- Console shows different input vs output samples
- Output waterfall visually cleaner than input
- Playback has audible noise reduction
- Extreme settings (NOISE_GAIN=0) produce near-silence

**Verification Steps:**
1. Load Pink Noise @ 10dB SNR
2. Process with default parameters
3. Check console for "Difference" array with non-zero values
4. Compare waterfalls - output should have less low-level noise
5. Play both - output should sound cleaner

---

## Key Takeaways for GPU Programming

1. **Initialize all buffers explicitly** - Don't assume zero is a safe default
2. **Match loop bounds to buffer sizes** - Different buffers may have different sizes
3. **Validate dispatch sizes** - Must match shader bounds and buffer capacity
4. **Add debug logging early** - Catch issues before they cascade
5. **Test with extreme parameters** - Makes bugs obvious during development

---

## Bug #4: Missing COPY_SRC Buffer Usage Flags

### Symptom
Debug functions (`debugNoiseProfile()`, FFT magnitude readback) returned all zeros even though buffers were initialized with non-zero values.

### Root Cause
GPU buffers were created without `GPUBufferUsage.COPY_SRC` flag, which is required to copy data from GPU back to CPU for debugging:

```javascript
// WRONG - can't read back from GPU
noiseProfile = device.createBuffer({
    size: WATERFALL_WIDTH * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
});

fftBuffer = device.createBuffer({
    size: FFT_SIZE * 2 * 4,
    usage: GPUBufferUsage.STORAGE,
});
```

### Why This Broke Debugging
WebGPU buffer usage flags control what operations are allowed:
- `STORAGE`: Can be used in compute shaders (read/write)
- `COPY_DST`: Can be written to from CPU → GPU
- `COPY_SRC`: Can be read from GPU → CPU ← **MISSING!**

Without `COPY_SRC`, the `copyBufferToBuffer()` command silently failed or returned undefined data.

### Fix
Add `COPY_SRC` flag to any buffer you need to read back for debugging:

```javascript
// CORRECT - can read back
noiseProfile = device.createBuffer({
    size: WATERFALL_WIDTH * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC,
});

fftBuffer = device.createBuffer({
    size: FFT_SIZE * 2 * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
});
```

### Lesson Learned
**Plan for debugging from the start.** Add `COPY_SRC` to buffers you might need to inspect, even during development. WebGPU's explicit buffer usage flags catch errors but can make debugging harder if you forget them.

---

## Bug #5: Binary Gate Instead of Spectral Subtraction

### Symptom
Noise reduction had no audible effect. RMS ratio was ~1.0 (meaning output ≈ input) even with extreme settings like `NOISE_GAIN = 0.0`.

### Root Cause
Implemented a simple binary gate instead of proper spectral subtraction:

```wgsl
// WRONG - binary gate
if (signalMagnitude > noiseMagnitude) {
    gain = SIGNAL_GAIN;  // 1.0 - no reduction!
} else {
    gain = NOISE_GAIN;   // 0.2 - reduce by 80%
}
processedFFTBuffer[k] = fftBuffer[k] * gain;
```

### Why This Didn't Work
**Diagnostic data at 5.0s:**
- FFT magnitudes (speech range): 0.237 - 1.495
- Noise profile: 0.038 - 1.134

When speech is present, `signalMagnitude > noiseMagnitude` for most frequency bins, so the shader applied `SIGNAL_GAIN = 1.0` (no change). Only bins where current magnitude ≤ noise profile got reduced, which was rare during speech.

**The algorithm was a noise gate, not noise reduction:**
- Voice active → most bins get gain 1.0 → no effect
- Voice silent → some bins get gain 0.2 → only helps in silence

### The Conceptual Mistake
Noise reduction should **subtract the noise energy** from the signal, not gate it:
- Speech + Noise has magnitude `S + N`
- We want to recover `S` by computing `(S + N) - N`
- Binary gate just checks if `S + N > N` and keeps everything or removes everything

### Fix
Implement spectral subtraction that removes noise energy:

```wgsl
let noiseMagnitude = noiseProfile[k];
let signalMagnitude = length(fftBuffer[k]);

// Subtract noise with oversubtraction factor
let cleanMagnitude = max(0.0, signalMagnitude - NOISE_SUPPRESSION_FACTOR * noiseMagnitude);
let gain = cleanMagnitude / max(signalMagnitude, 0.001);  // Avoid div by zero

processedFFTBuffer[k] = fftBuffer[k] * gain;
```

Where `NOISE_SUPPRESSION_FACTOR` (typically 2.0-3.0) controls aggressiveness. Higher values remove more noise but can introduce artifacts.

### Key Parameters
After this fix, the system has three independent parameters:

1. **ALPHA_DECAY** (0.001-0.1): How fast noise profile adapts to new minimums
   - Used in: Noise profile update shader
   - Smaller = slower, more stable estimate

2. **NOISE_SUPPRESSION_FACTOR** (1.0-5.0): How aggressively to subtract noise
   - Used in: Spectral subtraction calculation
   - Larger = more noise removed, more artifacts

3. **NOISE_FLOOR** (optional, 0.1): Minimum gain to prevent musical noise
   - Prevents gain from going to pure zero
   - Reduces artifacts at cost of some residual noise

### Lesson Learned
**Understand the difference between noise gating and noise reduction:**
- **Noise gate**: If signal < threshold, mute it. Binary on/off. Doesn't work when noise and signal overlap.
- **Noise reduction/subtraction**: Estimate noise energy and subtract it from the signal. Works even when speech and noise are simultaneous.

For speech in noisy environments, spectral subtraction is essential because speech and noise are always present together in the frequency domain.

---

## Updated Summary Table

| Bug | Impact | Root Cause | Fix |
|-----|--------|------------|-----|
| Uninitialized Buffer | No noise reduction | Started at 0 instead of high value | Initialize with 1000.0 |
| Out-of-Bounds Access | Undefined behavior | Used FFT_SIZE instead of WATERFALL_WIDTH | Check k < WATERFALL_WIDTH |
| Wrong Dispatch Size | Excessive shader invocations | Copy-paste from different pipeline | Use WATERFALL_WIDTH / 64 |
| Missing COPY_SRC Flags | Debug functions showed zeros | Forgot buffer usage flag for GPU→CPU | Add COPY_SRC to buffers |
| Binary Gate Algorithm | No audible effect | Used if/else instead of subtraction | Spectral subtraction formula |

---

## Date Fixed
2025-11-23

## Related Files
- `webgpu-audio-waterfall.html` (lines 343-367: buffer initialization with COPY_SRC)
- `webgpu-audio-waterfall.html` (lines 462-489: spectral subtraction shader)
- `webgpu-audio-waterfall.html` (lines 552-598: noise update shader)
- `webgpu-audio-waterfall.html` (lines 1352-1389: diagnostic logging)

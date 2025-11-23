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

## Date Fixed
2025-11-23

## Related Files
- `webgpu-audio-waterfall.html` (lines 358-366: buffer initialization)
- `webgpu-audio-waterfall.html` (lines 552-575: noise update shader)
- `webgpu-audio-waterfall.html` (lines 459-493: noise reduction shader)
- `webgpu-audio-waterfall.html` (line 1282: dispatch fix)

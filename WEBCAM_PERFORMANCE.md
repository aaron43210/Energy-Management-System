# Webcam Performance Optimization Guide

## Performance Settings

The webcam stream has been optimized for better performance. You can adjust these settings in `backend/webcam_stream.py`:

### Current Optimizations (Line 29-34)

```python
# Performance optimization settings
self.frame_skip = 2  # Process every Nth frame for YOLO (1=all, 2=every other, 3=every third)
self.jpeg_quality = 75  # JPEG quality (0-100, lower=faster but lower quality)
self.target_fps = 15  # Target FPS for smoother streaming
self.resize_factor = 0.75  # Resize frames to 75% for faster processing
```

### Tuning Guide

**For FASTER performance** (if still slow):
- Increase `frame_skip` to `3` or `4` (process fewer frames)
- Decrease `jpeg_quality` to `60` or `50` (faster encoding)
- Decrease `resize_factor` to `0.5` (smaller frames for YOLO)
- Decrease `target_fps` to `10` (lower frame rate)

**For BETTER quality** (if performance is good):
- Decrease `frame_skip` to `1` (process every frame)
- Increase `jpeg_quality` to `85` or `90` (better image quality)
- Increase `resize_factor` to `1.0` (full resolution)
- Increase `target_fps` to `20` or `25` (smoother video)

### What Each Setting Does

1. **frame_skip** (default: 2)
   - Controls how often YOLO runs
   - `1` = every frame (slowest, most accurate)
   - `2` = every other frame (good balance)
   - `3` = every third frame (faster)
   - Detection results are reused for skipped frames

2. **jpeg_quality** (default: 75)
   - Image compression quality
   - `100` = best quality, largest files, slowest
   - `75` = good quality, good compression (recommended)
   - `50` = acceptable quality, fast encoding

3. **target_fps** (default: 15)
   - Maximum frames per second to stream
   - Lower = less CPU usage, choppier video
   - Higher = smoother video, more CPU usage

4. **resize_factor** (default: 0.75)
   - Scale frames before YOLO processing
   - `1.0` = full resolution (slowest, most accurate)
   - `0.75` = 75% size (good balance)
   - `0.5` = 50% size (fastest, less accurate)
   - Bounding boxes are automatically scaled back to full size

## Testing Performance

After changing settings, restart the backend:
```bash
# Stop the current backend (Ctrl+C)
# Restart with:
.venv/bin/uvicorn backend.api:app --port 8002 --reload
```

Then test webcam mode in the web interface.

## Expected Performance

With current settings on typical hardware:
- **FPS:** ~15 FPS
- **Latency:** ~100-200ms
- **CPU:** 30-50% on modern CPU
- **Bandwidth:** ~400-600 KB/s

## Hardware Recommendations

**For best performance:**
- CPU: Modern multi-core processor (i5 or better)
- RAM: 4GB+ available
- Camera: Built-in webcam or USB camera with 720p/1080p support

**If performance is poor:**
- Close other applications
- Use integrated/built-in webcam instead of external USB camera
- Reduce browser tabs
- Adjust settings above for faster performance

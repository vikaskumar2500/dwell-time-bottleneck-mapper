# YOLO video pipeline

## Baseline configuration

| Setting | Value | Reason |
|---|---|---|
| Detector | `yolo11n.pt` | Lightweight person-detection baseline |
| Person class | COCO class `0` | Filters unrelated objects before analytics |
| Tracker | `bytetrack.yaml` | Fast fixed-camera baseline without appearance embeddings |
| Confidence | `0.35` | Configurable starting threshold |
| NMS IoU | `0.70` | Configurable overlap threshold |
| Input size | `640` | Practical latency/accuracy starting point |
| Floor point | Bounding-box bottom-center | Simple approximation of contact with the floor |

All tunable values live in `config/store.sample.json`. A new camera must use zones drawn for its resized frame; the sample polygons are illustrative and should not be treated as calibrated retail zones.

## Data flow

```text
video frame -> YOLO person boxes -> ByteTrack IDs -> bottom-center points
            -> zone/dwell engine -> JSON, CSV, heatmap PNG
```

`persist=True` preserves tracker state across consecutive frames from one source. A new invocation creates a new model/tracker session, so IDs never represent persistent customer identity.

## Local smoke-test evidence

The Phase 4 gate was exercised on an Apple Silicon `arm64` MacBook Air with Python 3.9.6, Ultralytics 8.4.123, PyTorch 2.8.0, and OpenCV 4.14.0. The input was a 20-frame, 10 FPS local MP4 derived from the official Ultralytics sample image and processed at 1280×720.

The run produced four stable session tracks and 80 person detections, plus `report.json`, `zone_metrics.csv`, `heatmap.csv`, `heatmap.png`, and a readable annotated MP4. This proves integration and artifact generation; it is not an accuracy benchmark or evidence of retail generalization.

## Commands

```bash
pip install '.[video]'

# Recorded video
dwell-map video --source /path/to/store.mp4

# Optional annotated output and bounded test run
dwell-map video --source /path/to/store.mp4 --save-video --max-frames 300

# Default webcam
dwell-map video --source 0
```

## Known limitations

- Pretrained COCO person detection has not yet been evaluated on store-specific footage.
- Boxes and track IDs can fail under long occlusion, reflections, crowding, and severe camera perspective.
- Bottom-center points are image-space approximations until camera homography is added.
- Runtime depends on hardware, resolution, crowd density, codec, model, and output settings.
- Store-specific accuracy and resume metrics belong to Phase 5 evaluation, not this smoke test.

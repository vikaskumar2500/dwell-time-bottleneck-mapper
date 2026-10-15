"""Optional YOLO video adapter.

This module keeps computer-vision dependencies outside the analytics core. It
imports OpenCV and Ultralytics only when video processing is requested.
"""

import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from .analytics import TrafficAnalyzer
from .config import load_store_config
from .io import write_outputs
from .models import Observation

VideoSource = Union[str, int]


class VideoError(RuntimeError):
    """Raised when a video source or vision dependency cannot be used."""


def parse_video_source(value: str) -> VideoSource:
    """Convert a non-negative camera index to int and preserve paths/URLs."""
    stripped = value.strip()
    if not stripped:
        raise VideoError("video source must be non-empty")
    if stripped.isdigit():
        return int(stripped)
    return stripped


def observations_from_boxes(
    track_ids: Sequence[int],
    boxes_xyxy: Sequence[Sequence[float]],
) -> List[Observation]:
    """Convert tracked person boxes to anonymous bottom-center observations."""
    if len(track_ids) != len(boxes_xyxy):
        raise VideoError("track IDs and boxes must have the same length")
    observations = []
    for track_id, box in zip(track_ids, boxes_xyxy):
        if len(box) != 4:
            raise VideoError("each tracked box must contain x1, y1, x2, y2")
        x1, _y1, x2, y2 = (float(value) for value in box)
        if not all(math.isfinite(value) for value in (x1, x2, y2)):
            raise VideoError("tracked box coordinates must be finite")
        observations.append(Observation(str(track_id), (x1 + x2) / 2.0, y2))
    return observations


def _percentile_95(values: List[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _load_video_dependencies():
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO
    except ImportError as exc:
        raise VideoError("video dependencies are missing; install with: pip install '.[video]'") from exc
    return cv2, np, YOLO


def _source_kind(source: VideoSource) -> str:
    if isinstance(source, int):
        return "camera"
    if source.startswith(("rtsp://", "rtmp://", "http://", "https://")):
        return "stream"
    return "file"


def analyze_video(
    source: VideoSource,
    config_path: str,
    output_dir: str,
    *,
    save_video: bool = False,
    max_frames: Optional[int] = None,
) -> Dict[str, object]:
    """Run YOLO person tracking and the Phase 3 analytics pipeline."""
    if max_frames is not None and max_frames <= 0:
        raise VideoError("max_frames must be positive")
    cv2, np, yolo_class = _load_video_dependencies()
    config = load_store_config(config_path)
    kind = _source_kind(source)
    if kind == "file" and not Path(str(source)).is_file():
        raise VideoError(f"video file does not exist: {source}")

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise VideoError(f"cannot open {kind} source")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    has_stable_fps = math.isfinite(source_fps) and source_fps > 0
    writer_fps = source_fps if has_stable_fps else 25.0
    writer = None
    if save_video:
        writer = cv2.VideoWriter(
            str(output / "annotated.mp4"),
            cv2.VideoWriter_fourcc(*"mp4v"),
            writer_fps,
            (config.frame.width, config.frame.height),
        )
        if not writer.isOpened():
            capture.release()
            raise VideoError("cannot create annotated video")

    model = yolo_class(config.vision.model)
    analyzer = TrafficAnalyzer(config)
    latencies_ms: List[float] = []
    unique_tracks = set()
    frame_count = 0
    detection_count = 0
    started = time.perf_counter()

    try:
        while max_frames is None or frame_count < max_frames:
            success, frame = capture.read()
            if not success:
                break
            frame = cv2.resize(frame, (config.frame.width, config.frame.height))
            timestamp = frame_count / source_fps if has_stable_fps else time.perf_counter() - started
            inference_started = time.perf_counter()
            result = model.track(
                frame,
                persist=True,
                classes=[0],
                conf=config.vision.confidence,
                iou=config.vision.iou,
                imgsz=config.vision.image_size,
                tracker=config.vision.tracker,
                verbose=False,
            )[0]
            latencies_ms.append((time.perf_counter() - inference_started) * 1000)

            observations: List[Observation] = []
            if result.boxes is not None and result.boxes.id is not None:
                track_ids = result.boxes.id.int().cpu().tolist()
                boxes = result.boxes.xyxy.cpu().tolist()
                observations = observations_from_boxes(track_ids, boxes)
                unique_tracks.update(track_ids)
                detection_count += len(observations)
            analyzer.update(timestamp, observations)

            if writer is not None:
                annotated = result.plot()
                for zone in config.zones:
                    polygon = np.asarray(zone.polygon, dtype=np.int32)
                    cv2.polylines(annotated, [polygon], True, (255, 180, 0), 2)
                    cv2.putText(
                        annotated,
                        zone.name,
                        tuple(polygon[0]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (255, 180, 0),
                        2,
                    )
                for observation in observations:
                    cv2.circle(annotated, (round(observation.x), round(observation.y)), 5, (0, 255, 255), -1)
                writer.write(annotated)
            frame_count += 1
    finally:
        capture.release()
        if writer is not None:
            writer.release()

    if frame_count == 0:
        raise VideoError("source contained no readable frames")

    analyzer.finalize()
    elapsed = time.perf_counter() - started
    report = analyzer.report()
    report["privacy"]["frames_stored"] = save_video
    steady_latencies = latencies_ms[1:] if len(latencies_ms) > 1 else latencies_ms
    report["runtime"] = {
        "source_kind": kind,
        "model": config.vision.model,
        "tracker": config.vision.tracker,
        "frames_processed": frame_count,
        "source_fps": round(source_fps, 2) if has_stable_fps else None,
        "processing_fps": round(frame_count / elapsed, 2) if elapsed else 0.0,
        "mean_inference_ms": round(sum(latencies_ms) / len(latencies_ms), 2),
        "p95_inference_ms": round(_percentile_95(latencies_ms), 2),
        "warmup_frames": 1 if len(latencies_ms) > 1 else 0,
        "mean_steady_inference_ms": round(sum(steady_latencies) / len(steady_latencies), 2),
        "p95_steady_inference_ms": round(_percentile_95(steady_latencies), 2),
        "person_detections": detection_count,
        "unique_session_tracks": len(unique_tracks),
        "frame_width": config.frame.width,
        "frame_height": config.frame.height,
    }
    write_outputs(report, analyzer.heatmap, output_dir)

    normalized = np.asarray(analyzer.normalized_heatmap(), dtype=np.float32)
    heatmap = cv2.resize(normalized, (config.frame.width, config.frame.height), interpolation=cv2.INTER_NEAREST)
    colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
    cv2.imwrite(str(output / "heatmap.png"), colored)
    return report

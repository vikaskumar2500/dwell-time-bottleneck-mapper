import configparser
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MotError(ValueError):
    """Raised when a MOTChallenge sequence is missing or malformed."""


def _sequence_metadata(sequence: Path) -> Dict[str, object]:
    info_path = sequence / "seqinfo.ini"
    parser = configparser.ConfigParser()
    try:
        if not parser.read(str(info_path), encoding="utf-8"):
            raise OSError
        section = parser["Sequence"]
        metadata = {
            "name": section.get("name", sequence.name),
            "image_dir": section.get("imDir", "img1"),
            "frame_rate": section.getfloat("frameRate"),
            "length": section.getint("seqLength"),
            "width": section.getint("imWidth"),
            "height": section.getint("imHeight"),
            "extension": section.get("imExt", ".jpg"),
        }
    except (OSError, KeyError, ValueError, configparser.Error) as exc:
        raise MotError(f"invalid or missing sequence metadata: {info_path}") from exc
    if any(metadata[key] <= 0 for key in ("frame_rate", "length", "width", "height")):
        raise MotError("MOT sequence dimensions, length, and frame rate must be positive")
    return metadata


def _ground_truth(
    sequence: Path,
    length: int,
    frame_width: int,
    frame_height: int,
) -> Dict[int, List[Dict[str, object]]]:
    path = sequence / "gt" / "gt.txt"
    frames: Dict[int, List[Dict[str, object]]] = {index: [] for index in range(1, length + 1)}
    try:
        stream = path.open(newline="", encoding="utf-8")
    except OSError as exc:
        raise MotError(f"missing MOT ground truth: {path}") from exc
    try:
        for line_number, row in enumerate(csv.reader(stream), 1):
            if len(row) < 7:
                raise MotError(f"invalid ground-truth row {line_number}: expected at least 7 columns")
            frame, track_id = int(float(row[0])), int(float(row[1]))
            left, top, width, height = (float(value) for value in row[2:6])
            marked = int(float(row[6]))
            object_class = int(float(row[7])) if len(row) > 7 else 1
            if marked != 1 or object_class != 1 or frame not in frames:
                continue
            # MOT boxes may extend beyond the image when a person is only
            # partly visible. Keep their floor point on the nearest edge.
            x = min(float(frame_width), max(0.0, left + width / 2.0))
            y = min(float(frame_height), max(0.0, top + height))
            frames[frame].append({"track_id": str(track_id), "x": x, "y": y})
    except (ValueError, csv.Error) as exc:
        raise MotError(f"invalid MOT ground truth: {path}") from exc
    finally:
        stream.close()
    return frames


def _store_config(name: str, width: int, height: int) -> Dict[str, object]:
    first, second = width // 3, (2 * width) // 3
    return {
        "store_id": f"mot-{name}",
        "frame": {"width": width, "height": height},
        "zones": [
            {"id": "left", "name": "Left Area", "polygon": [[0, 0], [first, 0], [first, height], [0, height]]},
            {"id": "center", "name": "Center Area", "polygon": [[first, 0], [second, 0], [second, height], [first, height]]},
            {"id": "right", "name": "Right Area", "polygon": [[second, 0], [width, 0], [width, height], [second, height]]},
        ],
        "analytics": {
            "heatmap_cell_px": max(20, width // 32),
            "bottleneck_occupancy": 5,
            "bottleneck_min_seconds": 3,
            "dead_zone_max_visits": 0,
            "track_ttl_seconds": 1,
        },
        "vision": {
            "model": "yolo11n.pt",
            "tracker": "bytetrack.yaml",
            "confidence": 0.35,
            "iou": 0.7,
            "image_size": 640,
        },
    }


def prepare_mot_sequence(sequence_path: str, output_dir: str, *, create_video: bool = False) -> Dict[str, object]:
    sequence = Path(sequence_path)
    metadata = _sequence_metadata(sequence)
    frames = _ground_truth(
        sequence,
        int(metadata["length"]),
        int(metadata["width"]),
        int(metadata["height"]),
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    config_path = output / "store.json"
    config_path.write_text(
        json.dumps(
            _store_config(str(metadata["name"]), int(metadata["width"]), int(metadata["height"])),
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    tracks_path = output / "ground_truth.jsonl"
    with tracks_path.open("w", encoding="utf-8") as stream:
        for frame in range(1, int(metadata["length"]) + 1):
            record = {
                "timestamp": (frame - 1) / float(metadata["frame_rate"]),
                "observations": frames[frame],
            }
            stream.write(json.dumps(record) + "\n")

    video_path: Optional[Path] = None
    if create_video:
        video_path = output / "sequence.mp4"
        _write_video(sequence, metadata, video_path)

    person_boxes = sum(len(items) for items in frames.values())
    manifest = {
        "dataset_format": "MOTChallenge",
        "sequence": metadata["name"],
        "frames": metadata["length"],
        "frame_rate": metadata["frame_rate"],
        "person_boxes": person_boxes,
        "unique_tracks": len({item["track_id"] for items in frames.values() for item in items}),
        "config": str(config_path),
        "ground_truth": str(tracks_path),
        "video": str(video_path) if video_path else None,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _write_video(sequence: Path, metadata: Dict[str, object], output: Path) -> None:
    try:
        import cv2
    except ImportError as exc:
        raise MotError("video dependencies are missing; install with: pip install '.[video]'") from exc
    writer = cv2.VideoWriter(
        str(output),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(metadata["frame_rate"]),
        (int(metadata["width"]), int(metadata["height"])),
    )
    if not writer.isOpened():
        raise MotError(f"cannot create video: {output}")
    image_dir = sequence / str(metadata["image_dir"])
    try:
        for frame in range(1, int(metadata["length"]) + 1):
            path = image_dir / f"{frame:06d}{metadata['extension']}"
            image = cv2.imread(str(path))
            if image is None:
                raise MotError(f"missing or unreadable MOT frame: {path}")
            if image.shape[1] != metadata["width"] or image.shape[0] != metadata["height"]:
                raise MotError(f"frame dimensions do not match seqinfo.ini: {path}")
            writer.write(image)
    finally:
        writer.release()

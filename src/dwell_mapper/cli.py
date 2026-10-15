import argparse
import json

from .analytics import AnalyticsError, TrafficAnalyzer
from .config import ConfigError, load_store_config
from .evaluation import EvaluationError, evaluate_files
from .io import ObservationError, read_observations, write_outputs
from .mot import MotError, prepare_mot_sequence
from .synthetic import generate_demo
from .video import VideoError, analyze_video, parse_video_source


def analyze(config_path: str, input_path: str, output_dir: str) -> dict:
    analyzer = TrafficAnalyzer(load_store_config(config_path))
    for timestamp, observations in read_observations(input_path):
        analyzer.update(timestamp, observations)
    analyzer.finalize()
    report = analyzer.report()
    write_outputs(report, analyzer.heatmap, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(prog="dwell-map")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate-config", help="validate a store configuration")
    validate.add_argument("path", nargs="?", default="config/store.sample.json")
    generate = subcommands.add_parser("generate-demo", help="generate deterministic tracker observations")
    generate.add_argument("--output", default="data/sample/tracks.jsonl")
    run = subcommands.add_parser("analyze", help="analyze tracker observations")
    run.add_argument("--config", default="config/store.sample.json")
    run.add_argument("--input", default="data/sample/tracks.jsonl")
    run.add_argument("--output", default="outputs/demo")
    video = subcommands.add_parser("video", help="run YOLO tracking on a video or camera")
    video.add_argument("--source", required=True, help="video path, stream URL, or camera index")
    video.add_argument("--config", default="config/store.sample.json")
    video.add_argument("--output", default="outputs/video")
    video.add_argument("--save-video", action="store_true", help="write annotated.mp4 (contains raw imagery)")
    video.add_argument("--max-frames", type=int, help="stop after this many frames")
    evaluate = subcommands.add_parser("evaluate", help="compare a report with annotated ground truth")
    evaluate.add_argument("--report", default="outputs/demo/report.json")
    evaluate.add_argument("--ground-truth", default="evaluation/synthetic_ground_truth.json")
    evaluate.add_argument("--output", default="outputs/evaluation.json")
    mot = subcommands.add_parser("prepare-mot", help="prepare a MOTChallenge sequence for evaluation")
    mot.add_argument("--sequence", required=True, help="directory containing seqinfo.ini, img1, and gt")
    mot.add_argument("--output", default="data/processed/mot")
    mot.add_argument("--video", action="store_true", help="assemble image frames into sequence.mp4")
    args = parser.parse_args()

    try:
        if args.command == "validate-config":
            config = load_store_config(args.path)
            print(f"Valid configuration: {config.store_id} ({len(config.zones)} zones)")
        elif args.command == "generate-demo":
            generate_demo(args.output)
            print(f"Demo observations written to {args.output}")
        elif args.command == "analyze":
            report = analyze(args.config, args.input, args.output)
            print(json.dumps(report, indent=2))
        elif args.command == "video":
            report = analyze_video(
                parse_video_source(args.source),
                args.config,
                args.output,
                save_video=args.save_video,
                max_frames=args.max_frames,
            )
            print(json.dumps(report, indent=2))
        elif args.command == "evaluate":
            metrics = evaluate_files(args.report, args.ground_truth, args.output)
            print(json.dumps(metrics, indent=2))
        else:
            manifest = prepare_mot_sequence(args.sequence, args.output, create_video=args.video)
            print(json.dumps(manifest, indent=2))
    except (ConfigError, ObservationError, AnalyticsError, VideoError, EvaluationError, MotError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
